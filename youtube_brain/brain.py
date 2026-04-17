#!/usr/bin/env python3
"""
Knowledge Brain Agent
Aprende de videos de YouTube y cualquier fuente web (artículos, foros, Reddit,
documentación, etc.) y construye un cerebro de conocimiento interconectado.
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import anthropic
import requests
from bs4 import BeautifulSoup, Comment
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# Setup
client = anthropic.Anthropic()
BRAIN_DIR = Path(__file__).parent / "brain_data"
BRAIN_DIR.mkdir(exist_ok=True)
INDEX_FILE = BRAIN_DIR / "index.json"

# ---------------------------------------------------------------------------
# Brain storage helpers
# ---------------------------------------------------------------------------

def load_index() -> dict:
    if INDEX_FILE.exists():
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        # Retrocompatibilidad: asegurar que existan las listas de web sources
        if "web_sources" not in data:
            data["web_sources"] = []
        # Agregar campo "type" a videos existentes si no lo tienen
        for v in data["videos"]:
            if "type" not in v:
                v["type"] = "video"
        return data
    return {"videos": [], "web_sources": []}


def save_index(index: dict) -> None:
    INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def get_video_id(url: str) -> str:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"No se pudo extraer el ID del video de: {url}")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def extract_transcript(video_url: str) -> dict:
    """Extract transcript from a YouTube video."""
    try:
        video_id = get_video_id(video_url)
        api = YouTubeTranscriptApi()
        try:
            fetched = api.fetch(video_id, languages=["es", "en"])
        except NoTranscriptFound:
            fetched = api.fetch(video_id)

        segments = list(fetched)
        full_text = " ".join(s.text for s in segments)

        # Keep up to ~60 000 chars to capture long tutorials in full
        if len(full_text) > 60000:
            full_text = full_text[:60000] + "... [transcript truncado por longitud]"

        return {
            "success": True,
            "video_id": video_id,
            "video_url": video_url,
            "transcript": full_text,
            "total_segments": len(segments),
            "language": fetched.language_code,
        }
    except TranscriptsDisabled:
        return {"success": False, "error": "Los subtítulos están deshabilitados para este video."}
    except NoTranscriptFound:
        return {"success": False, "error": "No se encontró transcript para este video."}
    except VideoUnavailable:
        return {"success": False, "error": "El video no está disponible."}
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": f"Error inesperado: {exc}"}


def _url_to_id(url: str) -> str:
    """Generate a deterministic short ID from a URL for file naming."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def extract_web_content(url: str) -> dict:
    """Extract the main text content from any web page."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove non-content elements
        for tag in soup(
            ["script", "style", "nav", "header", "footer", "aside", "iframe",
             "noscript", "form", "button", "svg", "img", "figure", "figcaption",
             "advertisement", "ins"]
        ):
            tag.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Remove common ad / nav classes and ids
        noise_patterns = re.compile(
            r"(sidebar|nav|menu|footer|header|banner|ad-|ads-|cookie|popup|modal|social|share|comment-form)",
            re.IGNORECASE,
        )
        for el in soup.find_all(attrs={"class": noise_patterns}):
            el.decompose()
        for el in soup.find_all(attrs={"id": noise_patterns}):
            el.decompose()

        # Try to find the main content area
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", {"role": "main"})
            or soup.find("div", class_=re.compile(r"(content|post|entry|article)", re.I))
            or soup.body
            or soup
        )

        # Extract page title
        page_title = ""
        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()
        h1 = soup.find("h1")
        if h1:
            page_title = h1.get_text(strip=True) or page_title

        # Get clean text
        raw_text = main.get_text(separator="\n")

        # Clean up whitespace: collapse multiple blank lines, strip lines
        lines = [line.strip() for line in raw_text.splitlines()]
        clean_lines = []
        prev_blank = False
        for line in lines:
            if not line:
                if not prev_blank:
                    clean_lines.append("")
                prev_blank = True
            else:
                clean_lines.append(line)
                prev_blank = False
        full_text = "\n".join(clean_lines).strip()

        # Truncate if extremely long
        if len(full_text) > 60000:
            full_text = full_text[:60000] + "\n... [contenido truncado por longitud]"

        if len(full_text) < 50:
            return {
                "success": False,
                "error": "No se pudo extraer contenido significativo de la página. Puede ser una SPA o estar protegida.",
            }

        return {
            "success": True,
            "source_url": url,
            "source_id": _url_to_id(url),
            "page_title": page_title,
            "content": full_text,
            "content_length": len(full_text),
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout al intentar acceder a la URL."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "No se pudo conectar a la URL."}
    except requests.exceptions.HTTPError as exc:
        return {"success": False, "error": f"Error HTTP: {exc.response.status_code}"}
    except Exception as exc:
        return {"success": False, "error": f"Error inesperado al extraer contenido web: {exc}"}


def save_web_to_brain(
    source_url: str,
    title: str,
    source_type: str,
    summary: str,
    key_concepts: list[str],
    tags: list[str],
    credibility_score: int,
) -> dict:
    """Persist processed web source knowledge to local brain storage."""
    index = load_index()
    source_id = _url_to_id(source_url)

    existing_ids = {s["source_id"] for s in index["web_sources"]}
    if source_id in existing_ids:
        return {"success": False, "message": f"La fuente '{title}' ya está en el cerebro."}

    source_data = {
        "source_id": source_id,
        "source_url": source_url,
        "title": title,
        "source_type": source_type,
        "summary": summary,
        "key_concepts": key_concepts,
        "tags": tags,
        "credibility_score": max(1, min(5, credibility_score)),
        "learned_at": datetime.now().isoformat(),
    }

    source_file = BRAIN_DIR / f"web_{source_id}.json"
    source_file.write_text(json.dumps(source_data, indent=2, ensure_ascii=False), encoding="utf-8")

    index["web_sources"].append(
        {
            "source_id": source_id,
            "title": title,
            "type": "web",
            "source_type": source_type,
            "tags": tags,
            "credibility_score": source_data["credibility_score"],
            "learned_at": source_data["learned_at"],
        }
    )
    save_index(index)

    score_label = {1: "dudoso", 2: "anecdótico", 3: "razonable", 4: "bien fundamentado", 5: "autoritativo"}
    return {
        "success": True,
        "message": (
            f"Fuente web '{title}' guardada en el cerebro. "
            f"Credibilidad: {source_data['credibility_score']}/5 ({score_label.get(source_data['credibility_score'], '')})."
        ),
    }


def save_to_brain(
    video_id: str,
    video_url: str,
    title: str,
    summary: str,
    key_concepts: list[str],
    tags: list[str],
) -> dict:
    """Persist processed video knowledge to local brain storage."""
    index = load_index()

    existing_ids = {v["video_id"] for v in index["videos"]}
    if video_id in existing_ids:
        return {"success": False, "message": f"El video '{title}' ya está en el cerebro."}

    video_data = {
        "video_id": video_id,
        "video_url": video_url,
        "title": title,
        "summary": summary,
        "key_concepts": key_concepts,
        "tags": tags,
        "learned_at": datetime.now().isoformat(),
    }

    video_file = BRAIN_DIR / f"{video_id}.json"
    video_file.write_text(json.dumps(video_data, indent=2, ensure_ascii=False), encoding="utf-8")

    index["videos"].append(
        {
            "video_id": video_id,
            "title": title,
            "type": "video",
            "tags": tags,
            "learned_at": video_data["learned_at"],
        }
    )
    save_index(index)

    return {"success": True, "message": f"Video '{title}' guardado en el cerebro."}


def query_brain(question: str) -> dict:
    """Return all stored knowledge so the model can answer the question."""
    index = load_index()

    total_sources = len(index["videos"]) + len(index.get("web_sources", []))
    if total_sources == 0:
        return {
            "success": False,
            "message": "El cerebro está vacío. Aprende algunos videos o fuentes web primero.",
        }

    knowledge = []

    # Videos
    for meta in index["videos"]:
        path = BRAIN_DIR / f"{meta['video_id']}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            knowledge.append(
                {
                    "type": "video",
                    "title": data["title"],
                    "url": data["video_url"],
                    "summary": data["summary"],
                    "key_concepts": data["key_concepts"],
                    "tags": data["tags"],
                }
            )

    # Web sources
    for meta in index.get("web_sources", []):
        path = BRAIN_DIR / f"web_{meta['source_id']}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            knowledge.append(
                {
                    "type": "web",
                    "source_type": data.get("source_type", "artículo"),
                    "title": data["title"],
                    "url": data["source_url"],
                    "summary": data["summary"],
                    "key_concepts": data["key_concepts"],
                    "tags": data["tags"],
                    "credibility_score": data.get("credibility_score", 3),
                }
            )

    return {
        "success": True,
        "question": question,
        "knowledge_base": knowledge,
        "total_videos": len(index["videos"]),
        "total_web_sources": len(index.get("web_sources", [])),
        "total_sources": len(knowledge),
    }


def find_connections() -> dict:
    """Load all stored sources so the model can analyse cross-source connections."""
    index = load_index()

    total = len(index["videos"]) + len(index.get("web_sources", []))
    if total < 2:
        return {
            "success": False,
            "message": "Necesitas al menos 2 fuentes en el cerebro para encontrar conexiones.",
        }

    sources = []

    for meta in index["videos"]:
        path = BRAIN_DIR / f"{meta['video_id']}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            sources.append(
                {
                    "type": "video",
                    "title": data["title"],
                    "url": data["video_url"],
                    "summary": data["summary"],
                    "key_concepts": data["key_concepts"],
                    "tags": data["tags"],
                }
            )

    for meta in index.get("web_sources", []):
        path = BRAIN_DIR / f"web_{meta['source_id']}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            sources.append(
                {
                    "type": "web",
                    "source_type": data.get("source_type", "artículo"),
                    "title": data["title"],
                    "url": data["source_url"],
                    "summary": data["summary"],
                    "key_concepts": data["key_concepts"],
                    "tags": data["tags"],
                    "credibility_score": data.get("credibility_score", 3),
                }
            )

    return {"success": True, "sources": sources}


def list_knowledge() -> dict:
    """Return the index of all learned sources (videos + web)."""
    index = load_index()
    return {
        "total_videos": len(index["videos"]),
        "total_web_sources": len(index.get("web_sources", [])),
        "total": len(index["videos"]) + len(index.get("web_sources", [])),
        "videos": index["videos"],
        "web_sources": index.get("web_sources", []),
    }


def forget_video(video_id: str) -> dict:
    """Remove a video from the brain."""
    index = load_index()

    before = len(index["videos"])
    index["videos"] = [v for v in index["videos"] if v["video_id"] != video_id]

    if len(index["videos"]) == before:
        return {"success": False, "message": f"No se encontró el video con ID '{video_id}'."}

    path = BRAIN_DIR / f"{video_id}.json"
    if path.exists():
        path.unlink()

    save_index(index)
    return {"success": True, "message": f"Video '{video_id}' eliminado del cerebro."}


def forget_web_source(source_id: str) -> dict:
    """Remove a web source from the brain."""
    index = load_index()

    web_sources = index.get("web_sources", [])
    before = len(web_sources)
    index["web_sources"] = [s for s in web_sources if s["source_id"] != source_id]

    if len(index["web_sources"]) == before:
        return {"success": False, "message": f"No se encontró la fuente web con ID '{source_id}'."}

    path = BRAIN_DIR / f"web_{source_id}.json"
    if path.exists():
        path.unlink()

    save_index(index)
    return {"success": True, "message": f"Fuente web '{source_id}' eliminada del cerebro."}


# ---------------------------------------------------------------------------
# Tool schemas for Claude
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "extract_transcript",
        "description": (
            "Extrae el transcript (subtítulos) de un video de YouTube dado su URL. "
            "Úsala siempre antes de guardar un video en el cerebro."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "URL completa del video de YouTube.",
                }
            },
            "required": ["video_url"],
        },
    },
    {
        "name": "extract_web_content",
        "description": (
            "Extrae el contenido textual principal de cualquier página web (artículos, foros, "
            "Reddit, documentación, blogs, etc.). Úsala antes de guardar una fuente web en el cerebro."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL completa de la página web a extraer.",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "save_to_brain",
        "description": (
            "Guarda el conocimiento procesado de un video en el cerebro. "
            "Úsala después de extraer y analizar el transcript."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "video_id": {"type": "string", "description": "ID del video (11 chars)."},
                "video_url": {"type": "string", "description": "URL completa del video."},
                "title": {
                    "type": "string",
                    "description": "Título descriptivo del video (infiere uno si no está disponible).",
                },
                "summary": {
                    "type": "string",
                    "description": (
                        "Resumen analítico del contenido (300-500 palabras). "
                        "Incluye los argumentos principales, metodología si aplica y conclusiones."
                    ),
                },
                "key_concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de 5-15 conceptos clave extraídos del video.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags para categorizar: área de conocimiento, tema, audiencia, etc.",
                },
            },
            "required": ["video_id", "video_url", "title", "summary", "key_concepts", "tags"],
        },
    },
    {
        "name": "save_web_to_brain",
        "description": (
            "Guarda el conocimiento procesado de una fuente web en el cerebro. "
            "Úsala después de extraer y analizar el contenido con extract_web_content. "
            "Evalúa críticamente la credibilidad de la fuente antes de guardar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source_url": {"type": "string", "description": "URL completa de la fuente web."},
                "title": {
                    "type": "string",
                    "description": "Título descriptivo de la fuente (usa el de la página o infiere uno).",
                },
                "source_type": {
                    "type": "string",
                    "description": (
                        "Tipo de fuente: artículo, foro, reddit, documentación, blog, "
                        "tutorial, paper, wiki, opinión, noticia, otro."
                    ),
                },
                "summary": {
                    "type": "string",
                    "description": (
                        "Resumen analítico del contenido (300-500 palabras). "
                        "Incluye los argumentos principales, evidencia presentada y conclusiones. "
                        "Marca claims no verificables con [NO VERIFICADO]."
                    ),
                },
                "key_concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de 5-15 conceptos clave extraídos de la fuente.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags para categorizar: área de conocimiento, tema, audiencia, etc.",
                },
                "credibility_score": {
                    "type": "integer",
                    "description": (
                        "Puntuación de credibilidad de la fuente (1-5): "
                        "1=dudoso, 2=anecdótico, 3=razonable, 4=bien fundamentado, 5=fuente autoritativa."
                    ),
                },
            },
            "required": [
                "source_url", "title", "source_type", "summary",
                "key_concepts", "tags", "credibility_score",
            ],
        },
    },
    {
        "name": "query_brain",
        "description": (
            "Consulta el cerebro para responder preguntas basadas en todo el conocimiento almacenado "
            "(videos y fuentes web). Devuelve toda la base de conocimiento relevante."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Pregunta a responder usando el conocimiento del cerebro.",
                }
            },
            "required": ["question"],
        },
    },
    {
        "name": "find_connections",
        "description": (
            "Carga todas las fuentes aprendidas (videos y web) para analizar relaciones, "
            "patrones compartidos y conexiones entre ideas de distintas fuentes."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_knowledge",
        "description": "Lista todas las fuentes (videos y web) que el cerebro ha aprendido hasta ahora.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "forget_video",
        "description": "Elimina un video del cerebro por su ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "video_id": {
                    "type": "string",
                    "description": "ID del video a eliminar (11 chars).",
                }
            },
            "required": ["video_id"],
        },
    },
    {
        "name": "forget_web_source",
        "description": "Elimina una fuente web del cerebro por su ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "string",
                    "description": "ID de la fuente web a eliminar (16 chars hex).",
                }
            },
            "required": ["source_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def execute_tool(name: str, inputs: dict) -> str:
    dispatch = {
        "extract_transcript": lambda: extract_transcript(inputs["video_url"]),
        "extract_web_content": lambda: extract_web_content(inputs["url"]),
        "save_to_brain": lambda: save_to_brain(**inputs),
        "save_web_to_brain": lambda: save_web_to_brain(**inputs),
        "query_brain": lambda: query_brain(inputs["question"]),
        "find_connections": lambda: find_connections(),
        "list_knowledge": lambda: list_knowledge(),
        "forget_video": lambda: forget_video(inputs["video_id"]),
        "forget_web_source": lambda: forget_web_source(inputs["source_id"]),
    }
    fn = dispatch.get(name)
    if fn is None:
        return json.dumps({"error": f"Herramienta desconocida: {name}"})
    return json.dumps(fn(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Eres un agente inteligente especializado en aprender de múltiples fuentes \
— videos de YouTube, artículos web, foros, Reddit, documentación técnica y cualquier \
recurso online — para construir un "cerebro" de conocimiento interconectado.

## Tus capacidades

1. **Aprender de videos de YouTube** — Cuando el usuario comparte un URL de YouTube:
   - Extrae el transcript con `extract_transcript`
   - Analiza el contenido en profundidad
   - Guarda un resumen analítico, conceptos clave y tags con `save_to_brain`
   - Confirma lo que aprendiste y menciona los conceptos más interesantes

2. **Aprender de fuentes web** — Cuando el usuario comparte cualquier URL que NO sea YouTube:
   - Extrae el contenido con `extract_web_content`
   - Analiza el contenido aplicando pensamiento crítico
   - Evalúa la credibilidad de la fuente (ver sección de Pensamiento Crítico)
   - Guarda con `save_web_to_brain` incluyendo source_type y credibility_score
   - Confirma lo que aprendiste y menciona la credibilidad asignada

3. **Conectar ideas** — Cuando el usuario pide conexiones o comparaciones:
   - Carga todas las fuentes con `find_connections`
   - Identifica temas transversales, conceptos complementarios y posibles contradicciones
   - Presenta los insights que emergen de cruzar los conocimientos
   - Usa analogías y ejemplos concretos
   - Nota diferencias de credibilidad entre fuentes

4. **Responder preguntas** — Cuando el usuario hace una pregunta:
   - Usa `query_brain` para acceder al conocimiento almacenado
   - Cita las fuentes relevantes al responder (videos y web)
   - Distingue entre lo que sabes gracias a las fuentes y tu conocimiento general
   - Indica el nivel de credibilidad cuando cites fuentes web

5. **Gestionar el cerebro** — Listar fuentes, olvidar un video o fuente web específica, etc.

## Pensamiento Crítico

IMPORTANTE: NO tomes todo como verdadero. Evalúa la credibilidad de cada fuente.

- **Marca claims que no puedas verificar como [NO VERIFICADO]** en el resumen.
- **Si dos fuentes se contradicen, registra ambas posiciones** y señala la contradicción.
- **Asigna un credibility_score** a cada fuente web:
  - 1 = dudoso (fuente anónima, claims sin evidencia, clickbait)
  - 2 = anecdótico (experiencia personal, opinión sin datos)
  - 3 = razonable (artículo bien escrito, argumentos lógicos pero sin fuentes primarias)
  - 4 = bien fundamentado (cita fuentes, datos verificables, autor reconocido)
  - 5 = fuente autoritativa (documentación oficial, papers peer-reviewed, instituciones)
- **Considera el contexto**: un post de Reddit con 500 upvotes y discusión sana es más \
confiable que un blog sin comentarios. Documentación oficial siempre es 5.
- **Al responder preguntas**, prioriza fuentes de mayor credibilidad y advierte cuando \
la información solo proviene de fuentes de baja credibilidad.

## Detección automática del tipo de URL

- Si la URL contiene "youtube.com" o "youtu.be" → usa `extract_transcript` + `save_to_brain`
- Cualquier otra URL → usa `extract_web_content` + `save_web_to_brain`

## Estilo de respuesta
- Responde siempre en español a menos que se indique lo contrario
- Sé analítico, no solo descriptivo
- Cuando conectes ideas, crea narrativas significativas, no simples listas
- Usa emojis con moderación para estructurar la respuesta (🧠 📌 🔗 💡 ⚠️)
"""


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(user_message: str) -> None:
    messages: list[dict] = [{"role": "user", "content": user_message}]
    print()

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        tool_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" or not tool_blocks:
            for block in response.content:
                if block.type == "text":
                    print(block.text)
            break

        # Show tool activity and collect results
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tb in tool_blocks:
            label = {
                "extract_transcript": "Extrayendo transcript...",
                "extract_web_content": "Extrayendo contenido web...",
                "save_to_brain": "Guardando video en el cerebro...",
                "save_web_to_brain": "Guardando fuente web en el cerebro...",
                "query_brain": "Consultando el cerebro...",
                "find_connections": "Buscando conexiones...",
                "list_knowledge": "Listando conocimiento...",
                "forget_video": "Eliminando video...",
                "forget_web_source": "Eliminando fuente web...",
            }.get(tb.name, f"Ejecutando {tb.name}...")

            print(f"  🔧 {label}")
            result = execute_tool(tb.name, tb.input)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tb.id, "content": result}
            )

        messages.append({"role": "user", "content": tool_results})
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

BANNER = """
╔═══════════════════════════════════════════════════════════╗
║            🧠  Knowledge Brain Agent  🧠                  ║
╠═══════════════════════════════════════════════════════════╣
║  • Pega un URL de YouTube para aprender de un video       ║
║  • Pega cualquier URL web (artículo, foro, Reddit, docs)  ║
║  • "conectar"  → conexiones entre todas las fuentes       ║
║  • "listar"    → ver tu base de conocimiento              ║
║  • Cualquier pregunta sobre lo aprendido                  ║
║  • "salir"     → terminar                                 ║
╚═══════════════════════════════════════════════════════════╝
"""


def main() -> None:
    print(BANNER)

    while True:
        try:
            user_input = input("💬 Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 ¡Hasta luego!")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() in ("salir", "exit", "quit", "q"):
            print("👋 ¡Hasta luego!")
            break

        try:
            run_agent(user_input)
        except anthropic.APIError as exc:
            print(f"\n❌ Error de API: {exc}\n")
        except Exception as exc:
            print(f"\n❌ Error inesperado: {exc}\n")


if __name__ == "__main__":
    main()
