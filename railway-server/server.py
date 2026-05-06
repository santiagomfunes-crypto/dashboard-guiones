#!/usr/bin/env python3
"""
Servidor Railway — Altavista Otero
Endpoints de scraping + Sofía WhatsApp Bot
"""

import os
import re
import json
import uuid
import time
import threading
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional

import requests as http_requests
from flask import Flask, request, jsonify
from supabase import create_client, Client
import anthropic

app = Flask(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

PORT = int(os.environ.get("PORT", 8080))

# Supabase guiones (scraper / propiedades_mercado)
SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Supabase sfre-web (propiedades del agente + chat)
SFRE_SUPABASE_URL = os.environ.get("SFRE_SUPABASE_URL", "")
SFRE_SUPABASE_KEY = os.environ.get("SFRE_SUPABASE_SERVICE_KEY", "")

# API key para POST /properties
API_KEY = os.environ.get("API_KEY", "")

# WhatsApp Cloud API
WA_TOKEN      = os.environ.get("WHATSAPP_TOKEN", "")
WA_PHONE_ID   = os.environ.get("WHATSAPP_PHONE_ID", "")
WA_VERIFY     = os.environ.get("WHATSAPP_VERIFY_TOKEN", "altavista-sofia-2026")

# Santiago — número para recibir escalaciones (formato: 5492494XXXXXX)
SANTIAGO_PHONE = os.environ.get("SANTIAGO_PHONE", "")

# Anthropic
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# OpenAI — para transcripción de audios (Whisper)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "https://santiagomfunes-crypto.github.io")

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
}

# ── Clients ────────────────────────────────────────────────────────────────────

def _sfre_client() -> Client:
    if not SFRE_SUPABASE_URL or not SFRE_SUPABASE_KEY:
        raise ValueError("SFRE_SUPABASE_URL / SFRE_SUPABASE_SERVICE_KEY no configuradas")
    return create_client(SFRE_SUPABASE_URL, SFRE_SUPABASE_KEY)

def _guiones_client() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def _anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_KEY)


# ══════════════════════════════════════════════════════════════════════════════
# SOFÍA — WhatsApp Bot
# ══════════════════════════════════════════════════════════════════════════════

# ── WhatsApp API ───────────────────────────────────────────────────────────────

def wa_send(to: str, text: str) -> None:
    if not WA_TOKEN or not WA_PHONE_ID:
        print(f"[WhatsApp] Sin credenciales — mensaje no enviado a {to}")
        return
    url = f"https://graph.facebook.com/v20.0/{WA_PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    resp = http_requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"},
        timeout=10,
    )
    print(f"[WhatsApp send → {to}] {resp.status_code}")

# ── Supabase: leads y mensajes ─────────────────────────────────────────────────

def lead_get_or_create(phone: str) -> dict:
    sb = _sfre_client()
    res = sb.table("chat_leads").select("*").eq("phone", phone).execute()
    if res.data:
        lead = res.data[0]
        sb.table("chat_leads").update({"last_message_at": "now()"}).eq("id", lead["id"]).execute()
        return lead
    res = sb.table("chat_leads").insert({"phone": phone}).execute()
    return res.data[0]

def lead_update_name(lead_id: str, name: str) -> None:
    _sfre_client().table("chat_leads").update({"name": name}).eq("id", lead_id).execute()

def messages_get(lead_id: str, limit: int = 20) -> list:
    res = (
        _sfre_client()
        .table("chat_messages")
        .select("role, content")
        .eq("lead_id", lead_id)
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return [{"role": m["role"], "content": m["content"]} for m in (res.data or [])]

def message_save(lead_id: str, role: str, content: str) -> None:
    _sfre_client().table("chat_messages").insert(
        {"lead_id": lead_id, "role": role, "content": content}
    ).execute()

# ── Propiedades con ROI ────────────────────────────────────────────────────────

def _parse_num(s: str) -> Optional[float]:
    if not s:
        return None
    clean = re.sub(r"[^\d.,]", "", str(s)).replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None

def properties_context() -> str:
    sb = _sfre_client()
    res = sb.table("propiedades").select("*").eq("estado", "disponible").execute()
    props = res.data or []

    lines = []
    for p in props:
        parts = [f"*{p.get('titulo', '')}*"]
        parts.append(f"Tipo: {p.get('tipo', '')} | Modalidad: {p.get('modalidad', '')}")
        parts.append(f"Precio: {p.get('precio') or 'A consultar'}")
        if p.get("superficie"):
            parts.append(f"Superficie: {p['superficie']}")
        if p.get("dormitorios"):
            parts.append(f"Dormitorios: {p['dormitorios']}")
        if p.get("banos"):
            parts.append(f"Baños: {p['banos']}")
        if p.get("piso"):
            parts.append(f"Piso: {p['piso']}")
        if p.get("posicion") and p["posicion"] not in ("", "Indistinto"):
            parts.append(f"Posición: {p['posicion']}")
        if p.get("cochera") and p["cochera"] != "Sin cochera":
            parts.append(f"Cochera: {p['cochera']}")
        if p.get("alquiler_estimado"):
            parts.append(f"Alquiler estimado: {p['alquiler_estimado']}")
            alquiler = _parse_num(p["alquiler_estimado"])
            precio   = _parse_num(p["precio"])
            if alquiler and precio and precio > 0:
                roi = (alquiler * 12 / precio) * 100
                parts.append(f"ROI anual estimado: {roi:.1f}%")
        if p.get("descripcion"):
            parts.append(f"Descripción: {str(p['descripcion'])[:300]}")
        slug = p.get("slug", "")
        parts.append(f"Link: https://propiedades.santiagofunes.com.ar/propiedades/{slug}")
        lines.append("\n  ".join(parts))

    return "\n\n".join(lines) if lines else "No hay propiedades disponibles en este momento."

# ── Sistema prompt de Sofía ────────────────────────────────────────────────────

def sofia_system_prompt() -> str:
    props = properties_context()
    return f"""Sos Sofía, la asistente de Santiago Funes en Altavista Otero, inmobiliaria en Tandil.

## TU IDENTIDAD

Sos una persona real. Nunca digas que sos un bot, IA o asistente virtual. Si alguien te pregunta si sos robot o IA, respondé naturalmente: "Para nada jaja, soy Sofía, la asistente de Santiago 😊"
Santiago Funes es el dueño. Juan Ignacio Otero es Martillero Público (Mat. 1966, Dep. Judicial Azul).
Oficina: Av. Avellaneda 1140, Tandil. Tel: +54 9 2494 20-9464.

## CÓMO ESCRIBÍS

- Mensajes cortos. Máximo 3-4 líneas. Esto es WhatsApp, no un email.
- Tono cálido, directo, rioplatense. Como una colega de confianza.
- Usás frases como: "Dale", "Perfecto", "Mirá", "Contame", "¿Qué te parece...?", "Sin drama".
- Emojis con criterio: uno o dos por mensaje cuando viene natural. Nunca en exceso.
- Nunca usés listas largas con viñetas. Una cosa por vez.

## TU OBJETIVO PRINCIPAL

Agendar una visita. Todo el flujo de conversación lleva hacia ahí.
Vender por WhatsApp no es el objetivo — la visita es el cierre del chat.

## FLUJO DE CONVERSACIÓN

1. Saludá y presentate ("Hola, soy Sofía de Altavista").
2. Pedí el nombre en los primeros mensajes de forma natural: "¿Con quién hablo?"
3. Entendé qué busca: tipo de propiedad, zona, presupuesto, si es para vivir o invertir, urgencia.
4. Mostrá máximo 2 propiedades que calcen. No hagas listas largas.
5. Si no hay nada en la zona pedida, ofrecé las disponibles que más se acerquen.
6. Empujá hacia la visita: "¿Te parece que coordinamos para que la vayas a ver?"
7. Si acordás una visita, confirmá propiedad, dirección, día y horario.

## MANEJO DE OBJECIONES

- "Está caro" → "Entiendo. En esa zona con esas características está en línea con el mercado. ¿Qué es lo que más te importa de la propiedad?"
- "Lo voy a pensar" → "Claro, sin apuro. ¿Qué necesitarías ver para animarte a visitarla?"
- "Mandame más info" → "Dale, pero para mandarte solo lo que te sirve, contame un poco más qué buscás."
- "No tengo el dinero ahora" → "Entendido. ¿Es algo para más adelante o tenés un tiempo estimado en mente?"
- "Vi algo más barato en otro lado" → "Puede ser. Cada propiedad tiene su historia. ¿Querés que te cuente qué tiene esta de distinto?"

## DETECCIÓN DE PERFIL DEL LEAD

- Si manda mensajes rápidos y pregunta por visita → lead caliente, proponé fecha concreta hoy.
- Si es vago o dice "solo mirando" → paciente, hacé preguntas abiertas para entender qué busca.
- Si parece frustrado ("nada me convence", respuestas secas) → empático: "Contame qué es lo que más te importa y lo buscamos juntos."

## CUÁNDO ESCALAR A SANTIAGO

Si no podés responder algo, si el lead tiene una situación especial, o si hay que negociar:
"Esto te lo consulto con Santiago y te aviso en breve ✅"
Nunca inventes información que no tenés.

## PROPIEDADES DISPONIBLES HOY

{props}

Si no hay propiedades que calcen con lo que busca, decís:
"Ahora mismo no tenemos algo así disponible, pero si me dejás tus datos te aviso cuando entre algo que te sirva." Luego pedí nombre y mail/WhatsApp para el seguimiento.

## BARRIOS Y PROYECTOS DE TANDIL — referencia exacta

Las propiedades están listadas por dirección de calle. Usá este mapa para matchear con lo que pide el cliente:

- **Barrio El Pozo**: Alberdi 865 (fideicomiso Estudio Pascua, última unidad, piso 3)
- **Proyecto Roca / Garibaldi**: Edificio Garibaldi 431 (varios pisos y posiciones disponibles). Cuando pregunten por "Roca" o "Garibaldi", mencioná el edificio y avisales que les vas a mandar la ficha del proyecto.
- **Roca, Avellaneda, Sarmiento, Constitución, Uriburu**: son nombres de calles en Tandil (no barrios). Matchear por nombre de calle en el listado de propiedades.
- Si no tenés propiedades en la zona exacta que piden, mostrá las más cercanas o similares y preguntá si alguna les interesa.

No mencionés otras inmobiliarias ni comparés precios de mercado. Respondé siempre en español rioplatense."""

# ── Audio: descarga y transcripción ───────────────────────────────────────────

def wa_download_media(media_id: str) -> Optional[bytes]:
    try:
        meta = http_requests.get(
            f"https://graph.facebook.com/v20.0/{media_id}",
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
            timeout=10,
        )
        media_url = meta.json().get("url")
        if not media_url:
            return None
        file_resp = http_requests.get(
            media_url,
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
            timeout=30,
        )
        return file_resp.content
    except Exception as e:
        print(f"[Audio download] {e}")
        return None

def transcribe_audio(audio_bytes: bytes) -> Optional[str]:
    if not OPENAI_KEY:
        return None
    try:
        import openai, io
        client = openai.OpenAI(api_key=OPENAI_KEY)
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.ogg"
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            language="es",
        )
        return result.text
    except Exception as e:
        print(f"[Whisper] {e}")
        return None

# ── Respuesta de Sofía ─────────────────────────────────────────────────────────

def sofia_reply(history: list, user_message: str) -> str:
    messages = history + [{"role": "user", "content": user_message}]
    client = _anthropic_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=sofia_system_prompt(),
        messages=messages,
    )
    return response.content[0].text

def needs_escalation(text: str) -> bool:
    keywords = ["te lo consulto", "consulto con santiago", "te paso con santiago", "aviso en breve"]
    return any(kw in text.lower() for kw in keywords)

def notify_escalation(lead: dict, last_user_message: str) -> None:
    if not SANTIAGO_PHONE:
        return
    name = lead.get("name") or "Sin nombre"
    phone = lead.get("phone", "")
    msg = (
        f"⚠️ *Sofía escaló una conversación*\n"
        f"Lead: {name} (+{phone})\n"
        f"Último mensaje: {last_user_message}\n"
        f"Respondele desde tu número si querés tomar el hilo."
    )
    wa_send(SANTIAGO_PHONE, msg)

# ── Debounce: agrupa mensajes en ráfaga ───────────────────────────────────────

_pending: dict = {}        # phone → {'timer': Timer, 'texts': [str]}
_pending_lock = threading.Lock()
DEBOUNCE_SECS = 4.0        # segundos de silencio antes de procesar

def _fire(phone: str) -> None:
    with _pending_lock:
        entry = _pending.pop(phone, None)
    if not entry:
        return
    combined = "\n".join(entry['texts'])
    print(f"[WA batch {phone}] {len(entry['texts'])} msgs → procesar")
    _handle_message(phone, combined)

def _handle_message(from_phone: str, user_text: str) -> None:
    try:
        lead    = lead_get_or_create(from_phone)
        lead_id = lead["id"]
        history = messages_get(lead_id)
        reply   = sofia_reply(history, user_text)
        message_save(lead_id, "user", user_text)
        message_save(lead_id, "assistant", reply)
        wa_send(from_phone, reply)
        # Auto-enviar PDF si menciona proyecto Roca
        if any(k in user_text.lower() for k in ["roca", "garibaldi", "proyecto roca"]):
            wa_send_doc(
                from_phone,
                "https://bsvcorcwcijpvwzxjzgu.supabase.co/storage/v1/object/public/propiedades/proyecto-roca.pdf",
                "Proyecto-Roca-Altavista.pdf"
            )
        if needs_escalation(reply):
            notify_escalation(lead, user_text)
    except Exception as e:
        print(f"[WA Error] {e}")

# ── Envío de documentos PDF ────────────────────────────────────────────────────

def wa_send_doc(to: str, doc_url: str, filename: str) -> None:
    if not WA_TOKEN or not WA_PHONE_ID:
        return
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {"link": doc_url, "filename": filename},
    }
    resp = http_requests.post(
        f"https://graph.facebook.com/v20.0/{WA_PHONE_ID}/messages",
        json=payload,
        headers={"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"},
        timeout=10,
    )
    print(f"[WA doc → {to}] {resp.status_code}")

# ── Webhook WhatsApp ───────────────────────────────────────────────────────────

@app.route("/whatsapp/webhook", methods=["GET"])
def wa_verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == WA_VERIFY:
        print("[Webhook] Verificación OK")
        return challenge, 200
    return "Forbidden", 403

@app.route("/whatsapp/webhook", methods=["POST"])
def wa_receive():
    data = request.get_json(silent=True) or {}
    try:
        entry   = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value   = changes.get("value", {})
        msgs    = value.get("messages", [])

        if not msgs:
            return "ok", 200

        msg      = msgs[0]
        msg_type = msg.get("type")

        if msg_type == "text":
            user_text = msg["text"]["body"]
        elif msg_type == "audio" and OPENAI_KEY:
            media_id    = msg.get("audio", {}).get("id")
            audio_bytes = wa_download_media(media_id) if media_id else None
            if not audio_bytes:
                return "ok", 200
            user_text = transcribe_audio(audio_bytes)
            if not user_text:
                return "ok", 200
            print(f"[Audio transcripto] {user_text[:80]}")
        else:
            return "ok", 200

        from_phone = msg["from"]
        print(f"[WA] {from_phone}: {user_text[:80]}")

        # Debounce: agrupa mensajes en ráfaga antes de responder
        with _pending_lock:
            if from_phone in _pending:
                _pending[from_phone]['timer'].cancel()
                _pending[from_phone]['texts'].append(user_text)
            else:
                _pending[from_phone] = {'texts': [user_text]}
            t = threading.Timer(DEBOUNCE_SECS, _fire, args=[from_phone])
            _pending[from_phone]['timer'] = t
            t.start()

    except Exception as e:
        print(f"[WA Error] {e}")

    return "ok", 200


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPING — endpoints existentes (sin cambios funcionales)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_html(url: str, referer: Optional[str] = None) -> Optional[str]:
    hdrs = dict(SCRAPE_HEADERS)
    if referer:
        hdrs["Referer"] = referer
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} para {url}")
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_num(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    clean = re.sub(r"[^\d.,]", "", s).replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None

def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s).replace("&amp;", "&").strip()

def first_match(pattern: str, text: str, flags=0) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None

def normalize_tipo(raw: str) -> str:
    r = raw.lower()
    if "departamento" in r or "depto" in r: return "departamento"
    if "ph" in r:                            return "PH"
    if "local" in r or "comercial" in r:     return "local"
    if "terreno" in r or "lote" in r:        return "terreno"
    if "oficina" in r:                       return "oficina"
    if "casa" in r or "chalet" in r:         return "casa"
    return raw.strip()

def clean_result(data: dict) -> dict:
    return {k: v for k, v in data.items()
            if v is not None and v != "" and not (isinstance(v, list) and len(v) == 0)}

def detect_portal(url: str) -> str:
    if "mercadolibre.com.ar" in url: return "mercadolibre"
    if "casasdehoy.com.ar"   in url: return "casasdehoy"
    if "zonaprop.com.ar"     in url: return "zonaprop"
    if "argenprop.com"       in url: return "argenprop"
    return "unknown"

def parse_casasdehoy(html: str) -> dict:
    result = {}
    title_text = first_match(r"<title>([\s\S]*?)</title>", html, re.IGNORECASE)
    if title_text:
        clean = strip_html(title_text).strip()
        result["tipo"] = normalize_tipo(clean)
        parts = clean.split(" - ")
        if len(parts) >= 2:
            result["barrio"] = parts[1].strip()[:100]
    precio_usd_raw = first_match(
        r'<h3[^>]*class="[^"]*azul[^"]*"[^>]*>[\s\S]*?U\$S\s*([\d.]+)', html, re.IGNORECASE
    )
    precio_ars_raw = first_match(
        r'<h3[^>]*class="[^"]*azul[^"]*"[^>]*>[\s\S]*?\$\s*([\d.]+)', html, re.IGNORECASE
    ) if not precio_usd_raw else None
    if precio_usd_raw:
        result["precio"]  = int(precio_usd_raw.replace(".", ""))
        result["moneda"]  = "USD"
    elif precio_ars_raw:
        result["precio"]  = int(precio_ars_raw.replace(".", ""))
        result["moneda"]  = "ARS"
    m2 = (
        first_match(r"fa-arrows[^>]*>[\s\S]{0,200}?([\d.,]+)\s*m(?:²|&sup2;)", html, re.IGNORECASE)
        or first_match(r"([\d.,]+)\s*m(?:²|&sup2;)", html, re.IGNORECASE)
    )
    if m2:  result["sup_total"] = parse_num(m2)
    m2c = first_match(r"([\d.,]+)\s*m(?:²|&sup2;)\s*(?:cub|cubierto)", html, re.IGNORECASE)
    if m2c: result["sup_cubierta"] = parse_num(m2c)
    d = first_match(r"[Dd]ormitorios?:\s*(\d+)", html)
    if d: result["dormitorios"] = int(d)
    a = first_match(r"[Aa]mbientes?:\s*(\d+)", html) or first_match(r"(\d+)\s*ambiente", html, re.IGNORECASE)
    if a: result["ambientes"] = int(a)
    b = first_match(r"[Bb]a[ñn]os?:\s*(\d+)", html)
    if b: result["banos"] = int(b)
    desc = first_match(
        r"Caracter[ií]sticas[\s\S]*?separator-line-gris[\s\S]*?<p[^>]*>([\s\S]*?)</p>", html, re.IGNORECASE
    )
    if desc:
        cd = strip_html(desc).strip()
        if cd and len(cd) > 5: result["descripcion"] = cd[:500]
    imagenes, seen = [], set()
    for m in re.finditer(r"fotos_nuevas/[^\s\"'<>]+", html):
        img_url = f"https://www.casasdehoy.com.ar/{m.group(0)}"
        if img_url not in seen:
            seen.add(img_url)
            imagenes.append(img_url)
    if imagenes: result["imagenes"] = imagenes[:20]
    return result

def parse_ml_api(item: dict) -> dict:
    result = {}
    price = item.get("price")
    currency = item.get("currency_id", "")
    if price:
        result["precio"] = price
        result["moneda"] = "USD" if currency == "USD" else "ARS"
    title = str(item.get("title", ""))
    if title:
        result["tipo"] = normalize_tipo(title)
        result["descripcion"] = title
    for a in item.get("attributes", []):
        attr_id = str(a.get("id", "")).upper()
        val = str(a.get("value_name") or a.get("value_struct", {}).get("number") or "")
        if   attr_id == "BEDROOMS"     and val: result["dormitorios"]  = int(val) if val.isdigit() else None
        elif attr_id == "ROOMS"        and val: result["ambientes"]    = int(val) if val.isdigit() else None
        elif attr_id == "BATHROOMS"    and val: result["banos"]        = int(val) if val.isdigit() else None
        elif attr_id == "COVERED_AREA":          result["sup_cubierta"] = parse_num(val)
        elif attr_id == "TOTAL_AREA":            result["sup_total"]    = parse_num(val)
        elif attr_id == "PROPERTY_TYPE" and val: result["tipo"]         = normalize_tipo(val)
        elif attr_id == "NEIGHBORHOOD"  and val: result["barrio"]       = val
    loc = item.get("location", {})
    if loc and not result.get("barrio"):
        result["barrio"] = str(
            loc.get("neighborhood", {}).get("name", "") or loc.get("city", {}).get("name", "")
        ) or None
    return result

def parse_mercadolibre_html(html: str) -> dict:
    result = {}
    pu = first_match(r"USD\s*([\d.,]+)", html, re.IGNORECASE)
    pa = first_match(r"\$\s*([\d.]+)", html)
    if pu:
        result["precio"] = parse_num(pu); result["moneda"] = "USD"
    elif pa:
        result["precio"] = parse_num(pa); result["moneda"] = "ARS"
    tipo_h1 = first_match(r'<h1[^>]*class="[^"]*ui-pdp-title[^"]*"[^>]*>(.*?)</h1>', html, re.IGNORECASE)
    if tipo_h1:
        result["tipo"] = normalize_tipo(strip_html(tipo_h1))
        if not result.get("descripcion"): result["descripcion"] = strip_html(tipo_h1)
    barrio = (
        first_match(r'class="[^"]*map__link[^"]*"[^>]*>(.*?)</a>', html, re.IGNORECASE)
        or first_match(r'"neighborhood"\s*:\s*"([^"]+)"', html, re.IGNORECASE)
    )
    if barrio: result["barrio"] = strip_html(barrio)
    if not result.get("ambientes"):
        m = first_match(r"(\d+)\s*ambiente", html, re.IGNORECASE)
        if m: result["ambientes"] = int(m)
    if not result.get("dormitorios"):
        m = first_match(r"(\d+)\s*dormitorio", html, re.IGNORECASE)
        if m: result["dormitorios"] = int(m)
    if not result.get("banos"):
        m = first_match(r"(\d+)\s*ba[ñn]o", html, re.IGNORECASE)
        if m: result["banos"] = int(m)
    if not result.get("sup_cubierta"):
        m = first_match(r"([\d.,]+)\s*m[²2]\s*cub", html, re.IGNORECASE)
        if m: result["sup_cubierta"] = parse_num(m)
    if not result.get("sup_total"):
        m = first_match(r"([\d.,]+)\s*m[²2]\s*tot", html, re.IGNORECASE) or first_match(r"([\d.,]+)\s*m²", html)
        if m: result["sup_total"] = parse_num(m)
    return result

def find_in_object(obj, key, depth=0):
    if depth > 8 or not obj or not isinstance(obj, (dict, list)):
        return None
    if isinstance(obj, list):
        for item in obj:
            found = find_in_object(item, key, depth + 1)
            if found is not None: return found
        return None
    if key in obj: return obj[key]
    for v in obj.values():
        found = find_in_object(v, key, depth + 1)
        if found is not None: return found
    return None

def parse_zonaprop(html: str) -> dict:
    result = {}
    for block in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE):
        try:
            data = json.loads(block)
            if data.get("description"):    result["descripcion"] = data["description"][:500]
            if data.get("name"):           result["tipo"]        = normalize_tipo(data["name"])
            if data.get("numberOfRooms"):  result["ambientes"]   = int(data["numberOfRooms"])
            if data.get("numberOfBedrooms"): result["dormitorios"] = int(data["numberOfBedrooms"])
            if data.get("numberOfBathroomsTotal"): result["banos"] = int(data["numberOfBathroomsTotal"])
            if data.get("floorSize", {}).get("value"): result["sup_cubierta"] = parse_num(str(data["floorSize"]["value"]))
            if data.get("address", {}).get("addressLocality"): result["barrio"] = data["address"]["addressLocality"]
            offers = data.get("offers")
            if offers:
                if isinstance(offers, list): offers = offers[0]
                if offers.get("price"):
                    result["precio"] = parse_num(str(offers["price"]))
                    result["moneda"] = "USD" if offers.get("priceCurrency") == "USD" else "ARS"
        except Exception:
            pass
    nd = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
    if nd:
        try:
            nd_data = json.loads(nd.group(1))
            listing = find_in_object(nd_data, "listing")
            if listing:
                attrs = find_in_object(listing, "attributes")
                if isinstance(attrs, list):
                    for a in attrs:
                        aid = str(a.get("id", "")).lower()
                        val = str(a.get("value", ""))
                        if   aid == "total_area":   result["sup_total"]    = parse_num(val)
                        elif aid == "covered_area": result["sup_cubierta"] = parse_num(val)
                        elif aid == "rooms":        result["ambientes"]    = int(val) if val.isdigit() else None
                        elif aid == "bedrooms":     result["dormitorios"]  = int(val) if val.isdigit() else None
                        elif aid == "bathrooms":    result["banos"]        = int(val) if val.isdigit() else None
        except Exception:
            pass
    if not result.get("precio"):
        pu = first_match(r"USD\s*([\d.,]+)", html, re.IGNORECASE)
        pa = first_match(r"\$\s*([\d.]+)", html)
        if pu:  result["precio"] = parse_num(pu); result["moneda"] = "USD"
        elif pa: result["precio"] = parse_num(pa); result["moneda"] = "ARS"
    if not result.get("ambientes"):
        m = first_match(r"(\d+)\s*ambiente", html, re.IGNORECASE)
        if m: result["ambientes"] = int(m)
    if not result.get("dormitorios"):
        m = first_match(r"(\d+)\s*dormitorio", html, re.IGNORECASE)
        if m: result["dormitorios"] = int(m)
    if not result.get("banos"):
        m = first_match(r"(\d+)\s*ba[ñn]o", html, re.IGNORECASE)
        if m: result["banos"] = int(m)
    return result

def parse_argenprop(html: str) -> dict:
    result = {}
    nd = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
    if nd:
        try:
            nd_data = json.loads(nd.group(1))
            listing = find_in_object(nd_data, "data") or find_in_object(nd_data, "property")
            if listing:
                tipo = str(find_in_object(listing, "propertyType") or find_in_object(listing, "type") or "")
                if tipo: result["tipo"] = normalize_tipo(tipo)
                price = find_in_object(listing, "price")
                if isinstance(price, dict):
                    result["precio"] = parse_num(str(price.get("amount") or price.get("value") or ""))
                    result["moneda"] = "USD" if str(price.get("currency", "")) == "USD" else "ARS"
                loc = find_in_object(listing, "location")
                if isinstance(loc, dict):
                    result["barrio"] = str(loc.get("neighborhood") or loc.get("city") or loc.get("name") or "")[:100] or None
                features = find_in_object(listing, "features")
                if isinstance(features, list):
                    for f in features:
                        k = str(f.get("name") or f.get("id") or "").lower()
                        v = str(f.get("value") or "")
                        if   "ambiente"  in k: result["ambientes"]    = int(v) if v.isdigit() else None
                        elif "dormitorio" in k or "habitaci" in k: result["dormitorios"] = int(v) if v.isdigit() else None
                        elif "baño"      in k: result["banos"]        = int(v) if v.isdigit() else None
                        elif "sup" in k and "cub" in k: result["sup_cubierta"] = parse_num(v)
                        elif "sup" in k and "tot" in k: result["sup_total"]    = parse_num(v)
                desc = str(find_in_object(listing, "description") or "")
                if desc: result["descripcion"] = desc[:500]
        except Exception:
            pass
    if not result.get("precio"):
        pu = first_match(r"USD\s*([\d.,]+)", html, re.IGNORECASE)
        pa = first_match(r"\$\s*([\d.]+)", html)
        if pu:   result["precio"] = parse_num(pu); result["moneda"] = "USD"
        elif pa: result["precio"] = parse_num(pa); result["moneda"] = "ARS"
    if not result.get("tipo"):
        h1 = first_match(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.IGNORECASE)
        if h1: result["tipo"] = normalize_tipo(strip_html(h1))
    return result

def fetch_from_supabase_guiones(fuente: str, fuente_id: str) -> Optional[dict]:
    sb = _guiones_client()
    if not sb:
        return None
    try:
        res = sb.table("propiedades_mercado")\
            .select("*")\
            .eq("fuente", fuente)\
            .eq("fuente_id", fuente_id)\
            .limit(1)\
            .execute()
        if res.data:
            row = res.data[0]
            return {
                "tipo":        normalize_tipo(str(row.get("tipologia") or "")) or None,
                "barrio":      row.get("zona"),
                "dormitorios": int(row["dormitorios"]) if row.get("dormitorios") else None,
                "sup_total":   float(row["metros_totales"]) if row.get("metros_totales") else None,
                "precio":      int(row["precio_usd"]) if row.get("precio_usd") else None,
                "moneda":      "USD" if row.get("precio_usd") else None,
                "descripcion": row.get("titulo"),
                "imagenes":    [row["imagen_url"]] if row.get("imagen_url") else None,
            }
    except Exception as e:
        print(f"[Supabase fallback] {e}")
    return None

def make_slug(titulo: str) -> str:
    base = re.sub(r"[^a-z0-9\s-]", "", titulo.lower())
    base = re.sub(r"\s+", "-", base.strip())[:50].strip("-")
    return f"{base}-{uuid.uuid4().hex[:6]}"

def upload_image(supabase: Client, image_url: str, slug: str, index: int) -> Optional[str]:
    try:
        resp = http_requests.get(image_url, timeout=15)
        resp.raise_for_status()
        ct  = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        ext = "jpg" if "jpeg" in ct else ct.split("/")[-1]
        path = f"{slug}/{int(time.time())}_{index}.{ext}"
        supabase.storage.from_("propiedades").upload(path, resp.content, {"content-type": ct})
        return supabase.storage.from_("propiedades").get_public_url(path)
    except Exception as e:
        print(f"[upload] imagen {index} falló: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# RUTAS HTTP
# ══════════════════════════════════════════════════════════════════════════════

def cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"]  = ALLOWED_ORIGIN
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, x-api-key"
    return resp

@app.after_request
def add_cors(resp):
    return cors_headers(resp)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "bot": "sofia"})

@app.route("/property")
def get_property():
    prop_url = request.args.get("url", "").strip()
    if not prop_url:
        return jsonify({"error": "Parámetro 'url' requerido"}), 400

    portal = detect_portal(prop_url)
    if portal == "unknown":
        return jsonify({"error": "Portal no soportado"}), 422

    print(f"Scraping [{portal}]: {prop_url}")

    if portal == "casasdehoy":
        cdh_match = re.search(r"-(\d+)-\d+\.html$", prop_url, re.IGNORECASE)
        if cdh_match:
            db_data = fetch_from_supabase_guiones("casasdehoy", cdh_match.group(1))
            if db_data:
                return jsonify(clean_result(db_data))

    if portal == "mercadolibre":
        ml_match = re.search(r"MLA[-\s]?(\d+)", prop_url, re.IGNORECASE)
        if ml_match:
            ml_id = f"MLA{ml_match.group(1)}"
            try:
                api_req = urllib.request.Request(
                    f"https://api.mercadolibre.com/items/{ml_id}",
                    headers={"Accept": "application/json"}
                )
                with urllib.request.urlopen(api_req, timeout=10) as r:
                    item = json.loads(r.read())
                    return jsonify(clean_result(parse_ml_api(item)))
            except Exception as e:
                print(f"ML API falló ({e}), cayendo a HTML")

    referers = {
        "casasdehoy":  "https://www.casasdehoy.com.ar/",
        "mercadolibre": "https://www.mercadolibre.com.ar/",
        "zonaprop":    "https://www.zonaprop.com.ar/",
        "argenprop":   "https://www.argenprop.com/",
    }
    html = fetch_html(prop_url, referer=referers.get(portal))
    if not html:
        return jsonify({"error": "No se pudo obtener la página"}), 502

    parsers = {
        "casasdehoy":   parse_casasdehoy,
        "mercadolibre": parse_mercadolibre_html,
        "zonaprop":     parse_zonaprop,
        "argenprop":    parse_argenprop,
    }
    return jsonify(clean_result(parsers[portal](html)))

@app.route("/properties", methods=["POST", "OPTIONS"])
def post_property():
    if request.method == "OPTIONS":
        return "", 204

    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "x-api-key inválida o ausente"}), 401

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Body JSON inválido"}), 400
    if not body.get("titulo"):
        return jsonify({"error": "Campo 'titulo' requerido"}), 422

    try:
        supabase = _sfre_client()
        image_urls = body.pop("image_urls", [])
        slug = body.get("slug") or make_slug(body["titulo"])
        body["slug"]   = slug
        body.setdefault("estado", "disponible")

        uploaded = [
            url for i, src in enumerate(image_urls)
            if (url := upload_image(supabase, src, slug, i))
        ]
        body["imagenes"] = uploaded

        result = supabase.table("propiedades").insert(body).execute()
        inserted = result.data[0] if result.data else {}
        return jsonify({
            "id":                inserted.get("id"),
            "slug":              inserted.get("slug"),
            "imagenes_subidas":  len(uploaded),
            "imagenes_fallidas": len(image_urls) - len(uploaded),
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        print(f"[POST /properties] {e}")
        return jsonify({"error": "Error interno"}), 500


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Altavista Otero — Servidor Railway ===")
    print(f"Puerto: {PORT}")
    print(f"Sofía WhatsApp: {'lista' if WA_TOKEN and WA_PHONE_ID else 'sin credenciales WA'}")
    print(f"Anthropic: {'configurado' if ANTHROPIC_KEY else 'NO CONFIGURADO'}")
    print(f"Supabase sfre-web: {'OK' if SFRE_SUPABASE_URL else 'NO CONFIGURADO'}")
    app.run(host="0.0.0.0", port=PORT)
