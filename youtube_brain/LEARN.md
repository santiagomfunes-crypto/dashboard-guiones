# YouTube Brain — Guiones SFRE

Sistema de aprendizaje para alimentar el proyecto de **guiones y marca personal** de Santiago Funes. Aprende de videos de YouTube, podcasts transcribibles y artículos web que aporten al posicionamiento de referente en real estate Tandil/interior argentino.

Este brain es **independiente** del de `~/Desktop/Claude/sfre-gestion/youtube_brain/` (ese es para gestión del negocio). Acá solo entra material que ayude a generar contenido, calibrar voz, o estudiar referentes de marca personal.

---

## Cómo aprender una fuente nueva

Opción 1 — manual:
```
"Aprendé de este video y guardalo en el brain: [URL]"
```

Opción 2 — correr el agente standalone:
```bash
cd /Users/santiagofunes/Desktop/herramientas/inmobiliaria/guiones/youtube_brain
python3 brain.py
```

El brain acepta:
- URLs de YouTube (extract_transcript)
- Cualquier URL web (extract_web_content: artículos, foros, Reddit, docs)

---

## Qué SÍ entra en este brain

- **Referentes de marca personal y real estate**: Beltrán Briones, Fran Castro (ROMS®), Tino Mossu, Club del Ladrillo, desarrolladores argentinos con marca personal.
- **Frameworks de contenido**: cómo estructurar reels/tiktoks, hooks, storytelling, puerta de atrás (Briones playbook), omnipresencia (Castro), PPOS (Curía).
- **Estudios de caso de creadores hispanohablantes** que crecieron rápido en 2025-2026.
- **Psicología del comprador inmobiliario argentino**: cómo decide, qué teme, qué lo mueve.
- **Finanzas personales argentinas aplicadas a real estate**: crédito hipotecario, dólar, plazo fijo vs ladrillo, impuestos.
- **Macro argentino con lectura para real estate**: solo cuando tenga lectura directa para generar contenido.

## Qué NO entra acá

- Gestión operativa del negocio (CRM, leads, procesos) → va al brain de `sfre-gestion`.
- Tasación, datos micro de propiedades → va a `tasador`.
- Contenido genérico de marketing que no se aplica a real estate argentino específicamente.

---

## Workflow de destilación

El brain no reescribe automáticamente — somos nosotros los que destilamos. Regla:

1. Cada vez que se aprenden **3+ videos sobre el mismo tema**, revisamos si vale destilarlos en un archivo de referencia en `referencia/` del proyecto guiones.
2. Ejemplo: 3 videos sobre el método Briones → destilar en `referencia/playbook-briones.md` (o actualizar `reference_podcast_mitico_fran_castro.md` en memoria).
3. Al destilar, **reescribimos** el archivo en vez de apilar. La versión anterior queda en git history si hace falta.
4. El brain_data/ es la "fuente primaria" — el destilado es la "síntesis útil".

Esto mantiene el contexto del proyecto lean (voz, framework, referencias vivas y cortas) mientras el brain acumula crudo.

---

## Fuentes prioritarias a aprender (roadmap)

### Marca personal / real estate Argentina
- [ ] **Podcast Mítico #30 con Fran Castro** (fuente primaria del sistema omnipresencia) — buscar si está en YouTube o solo Spotify
- [ ] Entrevistas a Beltrán Briones (especialmente las que explican el Método Briones y las decisiones de contenido)
- [ ] Videos recientes (marzo-abril 2026) de @beltran_briones en TikTok si hay reposts en YouTube
- [ ] Contenido de Club del Ladrillo si es argentino (verificar primero, podría ser el podcast español)

### Frameworks de contenido
- [ ] Alex Hormozi sobre ofertas y hooks (ya hay uno aprendido en sfre-gestion, puede valer referenciar)
- [ ] Daniel Priestley sobre posicionamiento como referente
- [ ] Iman Gadzhi sobre reels y captación

### Creadores hispanohablantes de nicho similar
- [ ] Investigar quién en México/España/Colombia está construyendo marca personal en real estate y cómo

---

## Estructura de los JSON aprendidos

El `brain.py` genera JSONs con esta forma (ver código en `brain.py` para detalle):

```json
{
  "video_id": "XXX",
  "title": "...",
  "summary": "...",
  "key_concepts": [...],
  "tags": [...],
  "learned_at": "ISO date"
}
```

Para fuentes web: mismo schema + `credibility_score` (1-5) + `source_type`.

---

## Videos / fuentes aprendidas

| ID | Tipo | Tema | Destilado en |
|---|---|---|---|
| CKxUe5QysG8 | video/tutorial | Meta Ads inmobiliario ES: videomarketing + landing IA → 7 leads/$480 en 30 días | — |
| pDOZbKWuHfI | video/tutorial | Lead form ads + carousel ads para real estate (básico, Lowell Brown Toronto) | — |
| bNGyk2UReZA | video/tutorial | Facebook Ads 2025 A-Z: maximize conversion leads, conditional logic, matriz de testing | — |
| empre_ar_ivan | web/podcast | Iván Briones: banca global → real estate | referencia/playbook-briones.md |
| detras_puesto_metodo | web/artículo | Método Briones: testeo contenido TikTok | referencia/playbook-briones.md |
| infobae_beltran_mar2026 | web/entrevista | Beltrán: contactos, contenido, mercado 2026 | referencia/playbook-briones.md |
| canal26_esquina | web/artículo | Formato torneo: mejor esquina/barrio por eliminación | referencia/playbook-briones.md |
| mejorinformado_mentalidad | web/entrevista | Briones: autenticidad, romper tabú ambición, impacto 14-55 | referencia/playbook-briones.md |
| mindlin_estrategia | web/artículo | Fórmula datos + provocación = leads reales | referencia/playbook-briones.md |
| p5YgvC6yzCs | video/tutorial | LLM Wiki (Karpathy) + Obsidian + Claude Code: alternativa al RAG, 95% ahorro tokens, 4 operaciones (ingest/query/lint/bulk) | — |

### Archivos en brain_data/ fuera de scope de este brain (→ sfre-gestion o descarte)

| Archivo | Razón |
|---|---|
| sistema_voz_inmobiliaria.json | Infraestructura técnica (Retell AI + Claude Code), no marca personal |
| benja_claude_design.json | Herramienta de diseño IA, no contenido de marca |
| agustin_tokens_optimization.json | Optimización de tokens, fuera de scope |
| benja_anthropic_changes.json | Novedades Anthropic, fuera de scope |
| claude_code_limits_optimization.json | Optimización Claude Code, fuera de scope |
| web_paperclip_tutorial.json | Tutorial Paperclip, fuera de scope |

---

## Dependencias

Ver `requirements.txt`. Si no están instaladas:
```bash
pip install -r requirements.txt
```

Requiere también `ANTHROPIC_API_KEY` en el environment para usar `brain.py` en modo CLI (no es necesario si solo se usa vía Claude Code con las tools extract_transcript / save_to_brain).
