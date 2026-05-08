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

# Santiago — número WhatsApp (para detección de mensajes entrantes)
SANTIAGO_PHONE = os.environ.get("SANTIAGO_PHONE", "")

# Telegram — notificaciones a Santiago sin restricción de ventana 24hs
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Anthropic
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# OpenAI — para transcripción de audios (Whisper)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

# Meta Lead Ads
META_PAGE_TOKEN  = os.environ.get("META_PAGE_TOKEN", "")
META_VERIFY_TOKEN = os.environ.get("META_LEADGEN_VERIFY_TOKEN", "altavista-leadgen-2026")
META_APP_SECRET  = os.environ.get("META_APP_SECRET", "")

# Mapeo form_id → propiedad (se pueden agregar desde env o hardcodear)
# Formato: "FORM_ID_1:Nombre Propiedad 1,FORM_ID_2:Nombre Propiedad 2"
_FORM_MAP_RAW = os.environ.get("META_FORM_MAP", "")
META_FORM_MAP: dict[str, str] = {}
for pair in _FORM_MAP_RAW.split(","):
    if ":" in pair:
        fid, fname = pair.split(":", 1)
        META_FORM_MAP[fid.strip()] = fname.strip()

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


# ── Pricing constants ──────────────────────────────────────────────────────────
# Claude Haiku 4.5 — https://www.anthropic.com/pricing
_HAIKU_INPUT_COST_PER_TOKEN  = 0.80 / 1_000_000   # $0.80 / MTok
_HAIKU_OUTPUT_COST_PER_TOKEN = 4.00 / 1_000_000   # $4.00 / MTok
# OpenAI Whisper — $0.006/min; asumimos ~30s promedio por audio de WhatsApp
_WHISPER_COST_PER_CALL = 0.003


def _log_api_usage(model: str, tokens_input: int = 0, tokens_output: int = 0,
                   cost_usd: float = 0.0, source: str = 'sofia') -> None:
    """Registra uso de API en Supabase para el monitor de costos."""
    try:
        _sfre_client().table("api_usage").insert({
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": round(cost_usd, 6),
            "source": source,
        }).execute()
    except Exception as e:
        print(f"[api_usage] {e}")


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

# ── Telegram: notificaciones a Santiago ───────────────────────────────────────

def tg_send(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Sin credenciales — mensaje no enviado")
        return
    try:
        resp = http_requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        print(f"[Telegram] {resp.status_code}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")

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

def lead_set_paused(lead_id: str, paused: bool) -> None:
    _sfre_client().table("chat_leads").update({"sofia_paused": paused}).eq("id", lead_id).execute()

def lead_set_unseen(lead_id: str) -> None:
    try:
        _sfre_client().table("chat_leads").update({"visto": False}).eq("id", lead_id).execute()
    except Exception as e:
        print(f"[lead_set_unseen] {e}")

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
    sb = _sfre_client()
    sb.table("chat_messages").insert(
        {"lead_id": lead_id, "role": role, "content": content}
    ).execute()
    try:
        sb.table("chat_leads").update({"last_message_at": "now()"}).eq("id", lead_id).execute()
    except Exception as e:
        print(f"[message_save] {e}")

# ── Propiedades con ROI ────────────────────────────────────────────────────────

_props_cache: dict = {"text": "", "ts": 0.0}
_PROPS_TTL = 300  # 5 minutos

def _parse_num(s: str) -> Optional[float]:
    if not s:
        return None
    clean = re.sub(r"[^\d.,]", "", str(s)).replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None

def properties_context() -> str:
    if time.time() - _props_cache["ts"] < _PROPS_TTL and _props_cache["text"]:
        return _props_cache["text"]
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

    result = "\n\n".join(lines) if lines else "No hay propiedades disponibles en este momento."
    _props_cache["text"] = result
    _props_cache["ts"]   = time.time()
    return result

# ── Sistema prompt de Sofía ────────────────────────────────────────────────────

def sofia_system_prompt() -> str:
    props = properties_context()
    return f"""Sos Sofía, la secretaria personal de Santiago Funes, corredor inmobiliario en Altavista Otero, Tandil.

## TU IDENTIDAD

Tu nombre completo es Sofía. Trabajás directamente con Santiago.
Sos una persona real. Nunca digas que sos un bot, IA o asistente virtual.
Si alguien te pregunta si sos robot o IA, respondé: "Para nada, soy Sofía, la secretaria de Santiago."
Si preguntan por quién sos: "Soy Sofía, trabajo con Santiago en todo lo que es atención y coordinación."
Santiago Funes es el corredor inmobiliario. Juan Ignacio Otero es Martillero Público (Mat. 1966, Dep. Judicial Azul).
Oficina: Av. Avellaneda 1140, Tandil. Tel: +54 9 2494 20-9464.

## CÓMO ESCRIBÍS

- Mensajes cortos. Máximo 3-4 líneas. Esto es WhatsApp, no un email. Si necesitás más de 5 líneas para explicar algo, mandá solo lo más importante y ofrecé ampliar después.
- NUNCA uses listas con guiones o viñetas. Escribí en párrafos cortos, una idea por vez.
- Tono profesional y cordial, rioplatense argentino. Representás a una inmobiliaria seria. Nada informal, nada de exceso de entusiasmo.
- Expresiones que SÍ usás: "Dale", "Perfecto", "Claro", "Mirá", "Entendido", "Sin problema", "Avisame", "Con gusto", "Muy bien".
- Expresiones que NUNCA usás: "¿Te late?", "órale", "chido", "ahorita", "tú", "vosotros", "¿vale?", "te acomodamos", "acomodar" (para horarios), "para ti", "para tí", "Buenísimo", "Bárbaro", "Genial", "¿Nos charlamos?", "¿Hablamos?". En su lugar: "Perfecto", "Muy bien", "Coordinamos", "Agendamos".
- Usás voseo siempre: "para vos", "¿querés?", "¿podés?", "¿tenés?", "¿sabés?". NUNCA tuteo. NUNCA "para ti".
- Emojis: con mucho criterio. En la mayoría de mensajes no usás ninguno. Solo si viene muy natural y ayuda al tono. Nunca más de uno por mensaje.
- Nunca usés listas largas con viñetas. Una cosa por vez.
- NUNCA uses asteriscos para negritas ni ningún tipo de formato markdown. Sin **, sin __, sin ##. Texto plano siempre, como un WhatsApp real.

## TU OBJETIVO PRINCIPAL

Entender qué busca la persona y mostrarle opciones que le sirvan. La visita es el paso natural cuando hay interés real — no el objetivo de cada mensaje.

## FLUJO DE CONVERSACIÓN

1. Saludá y presentate ("Hola, soy Sofía, la secretaria de Santiago").
2. Si no sabés el nombre, pedilo de forma natural una sola vez: "¿Con quién hablo?"
3. Entendé qué busca: tipo de propiedad, zona, presupuesto, si es para vivir o invertir.
4. Mostrá máximo 2 propiedades que calcen. No hagas listas largas.
5. Si no hay nada en la zona pedida, ofrecé las disponibles que más se acerquen.
6. Solo proponé una visita cuando el lead mostró interés concreto en una propiedad específica. No lo forzés antes de tiempo.
7. Si acordás una visita, confirmá propiedad, dirección, día y horario.

IMPORTANTE: No repitas "¿coordinamos una visita?" en cada respuesta. Leé el contexto. Si la persona todavía está explorando opciones o no encontró algo que le guste, seguí ayudándola a encontrar lo que busca. La visita se propone sola cuando hay fit real.

## REGLA CRÍTICA — CUANDO EL LEAD YA ELIGIÓ

Si el lead ya te dijo qué propiedad le interesa o qué unidad específica quiere ver:
- NO seguís preguntando preferencias ni mostrando otras opciones.
- NO hacés más preguntas de calificación.
- Vas DIRECTO a coordinar la visita: "Perfecto, ¿cuándo te viene bien para verla?"
- Una vez que dijo "me interesa esa", "quiero verla", "sí", "dale" → el siguiente mensaje tuyo es proponer un día y horario.
Ejemplo correcto: lead dice "me interesa el piso 4" → Sofía responde "Buenísimo. ¿Cuándo te viene bien para verla? ¿Mañana a la tarde o el finde?"
Ejemplo incorrecto: lead dice "me interesa el piso 4" → Sofía pregunta "¿Preferís frente o contrafrente?" ← NO HACER ESTO.

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

## PROPIETARIOS QUE QUIEREN TASAR O VENDER

Si alguien menciona que quiere vender su propiedad, tasar, o preguntar cuánto vale lo que tiene:
Respondé exactamente: "Perfecto. Le paso los datos a Santiago y él se va a comunicar con vos para coordinar la tasación."
No hagas más preguntas ni pidas detalles en ese momento. Santiago se encarga de eso.

## PRESUPUESTO — REGLA CRÍTICA

Si el lead te dice su presupuesto máximo, respetalo SIEMPRE. Nunca ofrezcas opciones que superen ese número.
Si no tenés nada dentro de ese presupuesto, sé honesta: "Mirá, en ese rango ahora mismo no tenemos nada disponible. Te anoto y te aviso si entra algo."
No insistás con propiedades fuera de presupuesto. Una vez que te dijeron el tope, ese es el filtro.

## CUÁNDO ESCALAR A SANTIAGO

Si no podés responder algo, si el lead tiene una situación especial, o si hay que negociar:
"Esto te lo consulto con Santiago y te aviso en breve."
Nunca inventes información que no tenés.

## PROPIEDADES DISPONIBLES HOY

{props}

Si no hay propiedades que calcen con lo que busca, decís:
"Ahora mismo no tenemos algo así disponible, pero si me dejás tu nombre y número te aviso cuando entre algo que te sirva."

## BARRIOS Y PROYECTOS DE TANDIL — referencia exacta

Las propiedades están listadas por dirección de calle. Usá este mapa para matchear con lo que pide el cliente:

Barrio El Pozo: Alberdi 865 (fideicomiso Estudio Pascua, última unidad, piso 3).
Garibaldi 431: Edificio en venta, varios pisos y posiciones disponibles. Es una propiedad del listado — mostrá las unidades disponibles. NO prometás mandar ficha ni PDF. Si quieren más detalles, decí "Te cuento lo que sé y si querés coordinamos una visita para que lo veas en persona".
Roca 36: Fideicomiso de construcción al costo (ver sección PROYECTO ROCA 36 más abajo). Es una propiedad DISTINTA a Garibaldi 431.
Roca, Avellaneda, Sarmiento, Constitución, Uriburu, Garibaldi son nombres de calles en Tandil (no barrios). Matchear por nombre de calle en el listado de propiedades.
Si no tenés propiedades en la zona exacta que piden, mostrá las más cercanas o similares y preguntá si alguna les interesa.

## PROYECTO ROCA 36 — Fideicomiso de construcción al costo

Cuando alguien pregunte por Roca o el proyecto fideicomiso, usá esta información:

Es un fideicomiso de construcción al costo. Desarrollador: Estudio Pascua. Comercialización exclusiva: Altavista Otero. Ubicación: Calle Roca 36, Tandil (esquina Avellaneda), zona centro a metros del Boulevard. El edificio tiene planta baja más 3 pisos con ascensor, unidades de 1 dormitorio.

Cada unidad tiene 52,90 m² cubiertos más 8 m² de balcón propio. Incluye calefacción por radiadores y caldera, y carpinterías con doble vidriado hermético (DVH). El edificio tiene ascensor. También hay locales comerciales en planta baja desde USD 66.000 y cocheras a USD 9.000.

Precio del departamento de 1 dormitorio: USD 102.500.

Forma de pago: reserva de USD 5.000, más un anticipo del 30% del total, y el saldo en cuotas mensuales en pesos indexadas al CAC (Cámara Argentina de la Construcción). Plazo de entrega: aproximadamente 24 meses desde inicio de obra.

Por qué conviene: comprás a precio de pozo antes de que suba, pagás el saldo en pesos (te protege de la inflación), y es un fideicomiso al costo —máxima transparencia, sin especulación. La zona centro de Tandil tiene alta demanda de alquiler.

Cómo manejarlo en la conversación: si preguntan por Roca 36, fideicomiso o proyecto Roca, contales brevemente. El PDF llega solo automáticamente, no lo prometás ni lo mencionés. Garibaldi 431 es una propiedad DISTINTA — no mezclar con Roca 36. Para Garibaldi no prometás fichas. Si preguntan por precio, decí "El departamento de 1 dorm arranca en USD 102.500 con financiación en pesos". Si preguntan cómo comprar, explicá el esquema reserva más 30% más cuotas CAC. Empujá hacia una reunión con Santiago para ver los planos en detalle.

## EDIFICIO CHACABUCO 977 — Departamentos a estrenar

Cuando alguien pregunte por departamentos y su presupuesto sea hasta USD 180.000, incluí siempre alguna unidad del Edificio Chacabuco 977.

Descripción del edificio: edificio de 5 pisos a estrenar en el centro de Tandil (Chacabuco 977, esquina Garibaldi). Desarrollador: Estudio Pascua. Calefacción individual por radiadores con caldera de alta eficiencia, aberturas con doble vidrio hermético (DVH), preinstalación de aire acondicionado, ascensor, portero eléctrico con visor, terraza accesible común con pergolado y vistas panorámicas. Cocheras con portón automático.

Unidades disponibles:
- 2 dormitorios (frente): 70,30 m² cubiertos + 3,20 m² balcón · 2 baños · lavadero · cochera · USD 175.000.
  Links: propiedades.santiagofunes.com.ar/propiedades/departamento-chacabuco-977-piso-1-frente-2dorm (y pisos 2, 3 y 4 con el mismo formato).
- 1 dormitorio (contrafrente) sin cochera: 45 m² cubiertos + balcón · USD 110.000.
- 1 dormitorio (contrafrente) con cochera: 45 m² cubiertos + balcón · USD 125.000.

Regla de presupuesto: para cualquier lead que busque departamento con presupuesto entre USD 100.000 y USD 200.000, mostrá siempre las unidades de Chacabuco 977 que correspondan. Incluí la unidad de 2 dormitorios (USD 175.000) aunque el presupuesto declarado sea algo menor (por ejemplo USD 160.000), porque el precio tiene margen de negociación real — puede que esa unidad entre dentro de su rango.

Precio negociable (regla interna — no lo decís espontáneamente): todas las unidades del Edificio Chacabuco 977 tienen margen de negociación. Si el lead dice que le parece caro, que está al límite del presupuesto, o pide si bajan el precio, respondé: "El precio tiene algo de margen. Te lo consulto con Santiago y te confirma." Luego escalá a Santiago.

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
        _log_api_usage(model="whisper-1", cost_usd=_WHISPER_COST_PER_CALL)
        return result.text
    except Exception as e:
        print(f"[Whisper] {e}")
        return None

# ── Respuesta de Sofía ─────────────────────────────────────────────────────────

def sofia_reply(history: list, user_message: str, lead_notas: str = "", escalate: bool = False, tasacion: bool = False) -> str:
    messages = history + [{"role": "user", "content": user_message}]
    system   = sofia_system_prompt()
    if lead_notas:
        system += f"\n\n## CONTEXTO DE ESTE LEAD\n{lead_notas}\nUsá este contexto para personalizar tu respuesta. No le preguntés cosas que ya respondió en el formulario."
    if tasacion:
        system += "\n\n## INSTRUCCIÓN ESPECIAL — TASACIÓN\nEste lead quiere vender o tasar su propiedad. Respondé: 'Perfecto. Le paso los datos a Santiago y él se va a comunicar con vos para coordinar la tasación.' Sin emojis. Sin más preguntas ni pedidos de datos."
    elif escalate:
        system += "\n\n## INSTRUCCIÓN ESPECIAL — HOY\nEste lead está mostrando interés concreto. Respondé con calidez y al final de tu mensaje incluí naturalmente: 'Ya le aviso a Santiago para que se comunique con vos hoy.' (con esas palabras exactas o muy similares, sin emojis al final)."
    client = _anthropic_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system,
        messages=messages,
    )
    _log_api_usage(
        model="claude-haiku-4-5-20251001",
        tokens_input=response.usage.input_tokens,
        tokens_output=response.usage.output_tokens,
        cost_usd=(response.usage.input_tokens * _HAIKU_INPUT_COST_PER_TOKEN
                  + response.usage.output_tokens * _HAIKU_OUTPUT_COST_PER_TOKEN),
    )
    text = response.content[0].text
    # Convertir markdown a formato WhatsApp
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)  # **negrita** → *negrita*
    text = re.sub(r'__(.+?)__',     r'*\1*', text)  # __negrita__ → *negrita*
    text = re.sub(r'#+\s',          '',      text)  # ## encabezados → sin formato
    # Eliminar listas con guión (Claude las copia del prompt)
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
    # Reemplazar mexicanismos que Claude sigue usando a pesar del prompt
    text = re.sub(r'¿[Tt]e late\b', '¿Te parece', text)       # preserva mayúscula tras ¿
    text = re.sub(r'\bte late\b', 'te parece', text, flags=re.IGNORECASE)  # resto de casos
    # Corregir construcción gramatical incorrecta común
    text = re.sub(r'¿[Tt]e gustaría coordinamos', '¿Coordinamos', text)
    text = re.sub(r'¿[Tt]e gustaría agendamos',   '¿Agendamos',   text)
    return text

def manager_reply(user_text: str) -> str:
    """Responde a Santiago con datos reales de los leads cuando le escribe a Sofía."""
    from datetime import datetime, timezone
    sb = _sfre_client()
    res = sb.table("chat_leads").select("*").order("last_message_at", desc=True).limit(15).execute()
    leads = res.data or []

    leads_ctx = ""
    for l in leads:
        name     = l.get("name") or "Sin nombre"
        phone    = l.get("phone", "")
        paused   = l.get("sofia_paused", False)
        last_msg = (l.get("last_message_at") or "")[:16]
        msgs     = messages_get(l["id"], limit=8)
        last_user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "—")
        estado = "🔥 CALIENTE — espera tu llamado" if paused else "activo"
        leads_ctx += f"\n• {name} (+{phone}) | {last_msg} | {estado}\n  Último: {last_user[:120]}\n"

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    client = _anthropic_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=f"""Sos Sofía, secretaria de Santiago Funes (corredor inmobiliario en Altavista Otero, Tandil).
Santiago te escribe directo para preguntarte sobre el estado de los leads. Respondele de forma clara, breve y útil.
Podés responder preguntas como "¿cómo va?", "¿qué está pasando?", "¿quién es el más caliente?", "¿qué quiere Fulano?", etc.
Hoy es {now} (hora Argentina).

ESTADO ACTUAL DE LOS LEADS:
{leads_ctx}
Respondé en español rioplatense, sin markdown. Sé directa y concisa.""",
        messages=[{"role": "user", "content": user_text}],
    )
    _log_api_usage(
        model="claude-haiku-4-5-20251001",
        tokens_input=response.usage.input_tokens,
        tokens_output=response.usage.output_tokens,
        cost_usd=(response.usage.input_tokens * _HAIKU_INPUT_COST_PER_TOKEN
                  + response.usage.output_tokens * _HAIKU_OUTPUT_COST_PER_TOKEN),
    )
    return response.content[0].text

def _handle_manager(user_text: str) -> None:
    try:
        print(f"[Manager] Santiago pregunta: {user_text[:60]}")
        reply = manager_reply(user_text)
        tg_send(reply)
    except Exception as e:
        print(f"[Manager] Error: {e}")

_TASACION_KW = [
    "tasar", "tasación", "tasacion",
    "quiero vender", "necesito vender", "pienso vender",
    "quisiera vender", "podría vender", "podria vender",
    "vender mi propiedad", "vender mi casa", "vender mi departamento",
    "vender mi depto", "vender mi terreno", "vender mi lote",
    "cuánto vale mi", "cuanto vale mi",
    "soy propietario", "soy propietaria", "soy dueño", "soy dueña",
    "tengo para vender",
]

def detect_tasacion(user_text: str) -> bool:
    t = user_text.lower()
    return any(k in t for k in _TASACION_KW)

def notify_tasacion(lead: dict, user_text: str) -> None:
    name  = lead.get("name") or "Sin nombre"
    phone = lead.get("phone", "")
    msg = (
        f"🏠 *Tasación — contacto entrante*\n\n"
        f"*{name}* \\(+{phone}\\)\n"
        f"_Dice:_ {user_text[:150]}\n\n"
        f"Sofía le dijo que te comunicás\\. Escribile:\n"
        f"https://wa\\.me/{phone}"
    )
    tg_send(msg)

def detect_urgency(user_text: str, history: list) -> tuple:
    """Clasifica si el lead muestra señales de alta intención. Retorna (is_urgent, summary)."""
    import json as _json
    messages = history[-6:] + [{"role": "user", "content": user_text}]
    try:
        client = _anthropic_client()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system="""Sos un clasificador de urgencia para un chatbot inmobiliario.
Analizá el último mensaje del lead y la conversación reciente.
Respondé SOLO JSON válido con dos campos:
- "urgent": true si el lead muestra señales claras de alta intención (quiere ver HOY o esta semana, tiene presupuesto definido, eligió una propiedad específica, dice "me interesa", "lo quiero", "¿cuándo puedo verlo?", "¿podemos firmar?", o similar)
- "summary": en una oración qué busca y por qué es urgente (para notificar al agente inmobiliario). Vacío si no es urgente.
Si no hay urgencia clara: {"urgent": false, "summary": ""}""",
            messages=messages,
        )
        _log_api_usage(
            model="claude-haiku-4-5-20251001",
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            cost_usd=(response.usage.input_tokens * _HAIKU_INPUT_COST_PER_TOKEN
                      + response.usage.output_tokens * _HAIKU_OUTPUT_COST_PER_TOKEN),
        )
        raw = response.content[0].text.strip()
        # Extraer JSON aunque Claude agregue texto antes o después
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            return False, ""
        result = _json.loads(json_match.group(0))
        return bool(result.get("urgent")), result.get("summary", "")
    except Exception as e:
        print(f"[urgency] {e}")
        return False, ""

def needs_escalation(text: str) -> bool:
    keywords = ["te lo consulto", "consulto con santiago", "te paso con santiago", "aviso en breve"]
    return any(kw in text.lower() for kw in keywords)

def notify_urgency(lead: dict, last_user_message: str, urgency_summary: str) -> None:
    """Notifica a Santiago que hay un lead caliente listo para tomar."""
    name  = lead.get("name") or "Sin nombre"
    phone = lead.get("phone", "")
    msg = (
        f"🔥 *Lead caliente — intervención inmediata*\n\n"
        f"*{name}* (+{phone})\n"
        f"{urgency_summary}\n\n"
        f"_Último mensaje:_ {last_user_message}\n\n"
        f"Sofía le dijo que te comunicás hoy\\. Escribile:\n"
        f"https://wa\\.me/{phone}"
    )
    tg_send(msg)

def notify_escalation(lead: dict, last_user_message: str) -> None:
    name = lead.get("name") or "Sin nombre"
    phone = lead.get("phone", "")
    msg = (
        f"⚠️ *Sofía escaló una conversación*\n\n"
        f"*{name}* \\(+{phone}\\)\n"
        f"_Último mensaje:_ {last_user_message}\n\n"
        f"Escribile: https://wa\\.me/{phone}"
    )
    tg_send(msg)

# ── Debounce: agrupa mensajes en ráfaga ───────────────────────────────────────

_pending: dict = {}        # phone → {'timer': Timer, 'texts': [str], 'profile_name': str}
_pending_lock = threading.Lock()
DEBOUNCE_SECS = 4.0        # segundos de silencio antes de procesar

def _fire(phone: str) -> None:
    with _pending_lock:
        entry = _pending.pop(phone, None)
    if not entry:
        return
    combined = "\n".join(entry['texts'])
    # Decodificar URL encoding si Meta mandó el texto encodificado
    try:
        import urllib.parse as _up
        decoded = _up.unquote(combined)
        if decoded != combined:
            print(f"[WA decode] URL-encoded → decodificado")
            combined = decoded
    except Exception:
        pass
    profile_name = entry.get('profile_name', '')
    print(f"[WA batch {phone}] {len(entry['texts'])} msgs → procesar")
    _handle_message(phone, combined, profile_name=profile_name)

def _handle_message(from_phone: str, user_text: str, profile_name: str = "") -> None:
    try:
        lead    = lead_get_or_create(from_phone)
        lead_id = lead["id"]
        # Capturar nombre del perfil WhatsApp si el lead no tiene nombre aún
        if profile_name and not lead.get("name"):
            lead_update_name(lead_id, profile_name)
            lead["name"] = profile_name  # actualizar localmente para notify_urgency
        # Siempre guardar el mensaje entrante y marcar lead como no visto
        message_save(lead_id, "user", user_text)
        lead_set_unseen(lead_id)
        # Si Sofía está pausada (Santiago tomó el control), no responder
        if lead.get("sofia_paused"):
            print(f"[WA] Sofía pausada para {from_phone} — mensaje guardado, sin respuesta")
            return
        history    = messages_get(lead_id, limit=20)
        lead_notas = lead.get("notas") or ""

        # Tasación: propietario que quiere vender — prioridad sobre urgencia normal
        is_tasacion = detect_tasacion(user_text)

        if is_tasacion:
            reply = sofia_reply(history, user_text, lead_notas, tasacion=True)
            message_save(lead_id, "assistant", reply)
            wa_send(from_phone, reply)
            notify_tasacion(lead, user_text)
            lead_set_paused(lead_id, True)
        else:
            # Detectar urgencia antes de generar la respuesta
            is_urgent, urgency_summary = detect_urgency(user_text, history)

            reply = sofia_reply(history, user_text, lead_notas, escalate=is_urgent)
            message_save(lead_id, "assistant", reply)
            wa_send(from_phone, reply)

            # Auto-enviar PDF del fideicomiso Roca 36
            roca_keywords = ["roca 36", "proyecto roca", "fideicomiso roca", "fideicomiso", "roca"]
            if any(k in user_text.lower() for k in roca_keywords) and "garibaldi" not in user_text.lower():
                wa_send_doc(
                    from_phone,
                    "https://bsvcorcwcijpvwzxjzgu.supabase.co/storage/v1/object/public/propiedades/proyecto-roca.pdf",
                    "Proyecto-Roca-Altavista.pdf"
                )
                message_save(lead_id, "assistant", "📄 [PDF enviado: Proyecto-Roca-Altavista.pdf]")

            # Urgencia detectada: notificar a Santiago y pausar Sofía
            if is_urgent:
                print(f"[WA] Lead caliente detectado: {from_phone} — {urgency_summary}")
                notify_urgency(lead, user_text, urgency_summary)
                lead_set_paused(lead_id, True)
            elif needs_escalation(reply):
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

# ══════════════════════════════════════════════════════════════════════════════
# META LEAD ADS — Webhooks oficiales
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_phone(raw: str) -> str:
    """Normaliza el teléfono al formato E.164 sin el +, p.ej. 5491112345678."""
    digits = re.sub(r"[^\d]", "", raw)
    # Si viene con código de país argentino (54) y tiene 13 dígitos → ok
    # Si viene sin código de país (empieza con 0 o 9) → agrega 54
    if digits.startswith("54") and len(digits) >= 12:
        return digits
    if digits.startswith("0"):
        digits = "54" + digits[1:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "54" + digits
    elif not digits.startswith("54"):
        digits = "54" + digits
    return digits

def _retrieve_lead(leadgen_id: str) -> Optional[dict]:
    """Llama a la Graph API para obtener los datos del lead."""
    if not META_PAGE_TOKEN:
        print("[LeadAds] META_PAGE_TOKEN no configurado")
        return None
    try:
        resp = http_requests.get(
            f"https://graph.facebook.com/v20.0/{leadgen_id}",
            params={"access_token": META_PAGE_TOKEN},
            timeout=10,
        )
        data = resp.json()
        if "error" in data:
            print(f"[LeadAds] Error API: {data['error']}")
            return None
        return data
    except Exception as e:
        print(f"[LeadAds] retrieve_lead error: {e}")
        return None

def _parse_lead_fields(field_data: list) -> dict:
    """Extrae todos los campos del formulario de Meta."""
    NAME_KEYS  = {"full_name", "nombre_completo", "nombre", "name"}
    PHONE_KEYS = {"phone_number", "telefono", "phone", "celular", "whatsapp"}
    result = {"name": "", "phone": "", "extras": {}}
    for f in field_data:
        key   = f.get("name", "").lower()
        value = (f.get("values") or [""])[0].strip()
        if not value:
            continue
        if key in NAME_KEYS:
            result["name"] = value
        elif key in PHONE_KEYS:
            result["phone"] = value
        else:
            # Cualquier otra pregunta del formulario (presupuesto, zona, etc.)
            result["extras"][f.get("name", key)] = value
    return result

def _build_form_notas(propiedad: str, nombre: str, extras: dict) -> str:
    """Construye el texto de notas con todo el contexto del formulario."""
    lines = [f"Origen: Meta Ads — {propiedad}"]
    if nombre:
        lines.append(f"Nombre declarado en formulario: {nombre}")
    for k, v in extras.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)

def _process_meta_lead(leadgen_id: str, form_id: str) -> None:
    """Recupera el lead de Meta y lo guarda en Supabase con todo el contexto del formulario."""
    lead_data = _retrieve_lead(leadgen_id)
    if not lead_data:
        return

    fields    = _parse_lead_fields(lead_data.get("field_data", []))
    phone_raw = fields["phone"]
    nombre    = fields["name"]
    extras    = fields["extras"]
    propiedad = META_FORM_MAP.get(form_id, "una de nuestras propiedades")
    phone     = _normalize_phone(phone_raw) if phone_raw else ""
    notas     = _build_form_notas(propiedad, nombre, extras)

    if not phone_raw:
        print(f"[LeadAds] Leadgen {leadgen_id} sin teléfono — guardando igualmente")

    try:
        sb = _sfre_client()
        existing = sb.table("chat_leads").select("id,notas").eq("phone", phone).execute() if phone else None
        if existing and existing.data:
            lead_id = existing.data[0]["id"]
            # Actualizar notas con el contexto del formulario
            sb.table("chat_leads").update({"notas": notas}).eq("id", lead_id).execute()
            print(f"[LeadAds] Lead existente {lead_id} enriquecido con datos del formulario")
        else:
            insert_data: dict = {"status": "nuevo", "notas": notas}
            if nombre: insert_data["name"]  = nombre
            if phone:  insert_data["phone"] = phone
            res     = sb.table("chat_leads").insert(insert_data).execute()
            lead_id = res.data[0]["id"]
            print(f"[LeadAds] Nuevo lead {lead_id} — {nombre} ({phone}) — {propiedad}")

        # El contexto del formulario ya queda en lead.notas — no hace falta guardarlo como mensaje.
        # Sofía lo recibe en el system prompt vía lead_notas en _handle_message().

    except Exception as e:
        print(f"[LeadAds] Error guardando lead: {e}")


@app.route("/meta/leadgen", methods=["GET"])
def meta_leadgen_verify():
    """Verificación del webhook de Meta."""
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        print("[LeadAds] Webhook verificado OK")
        return challenge, 200
    return "Forbidden", 403


@app.route("/meta/leadgen", methods=["POST"])
def meta_leadgen_receive():
    """Recibe notificaciones de nuevos leads desde Meta Lead Ads."""
    # Verificar firma HMAC si tenemos el app secret
    if META_APP_SECRET:
        import hmac, hashlib
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            META_APP_SECRET.encode(), request.data, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            print("[LeadAds] Firma inválida")
            return "Forbidden", 403

    data = request.get_json(silent=True) or {}
    if data.get("object") != "page":
        return "ok", 200

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "leadgen":
                continue
            val = change.get("value", {})
            leadgen_id = val.get("leadgen_id", "")
            form_id    = val.get("form_id", "")
            if leadgen_id:
                t = threading.Thread(target=_process_meta_lead, args=[leadgen_id, form_id], daemon=True)
                t.start()

    return "ok", 200


@app.route("/wa/send", methods=["POST"])
def wa_send_manual():
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    to      = body.get("to", "").strip()
    text    = body.get("text", "").strip()
    lead_id = body.get("lead_id", "").strip()
    if not to or not text:
        return jsonify({"error": "to y text requeridos"}), 400
    wa_send(to, text)
    if lead_id:
        message_save(lead_id, "assistant", text)
        # Auto-pausar Sofía cuando Santiago interviene manualmente
        try:
            _sfre_client().table("chat_leads").update({"sofia_paused": True}).eq("id", lead_id).execute()
        except Exception as e:
            print(f"[WA send] No se pudo pausar Sofía: {e}")
    return jsonify({"ok": True})


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

        # Log de statuses (entrega/lectura) — útil para debugging
        statuses = value.get("statuses", [])
        if statuses:
            for s in statuses:
                print(f"[WA status] {s.get('recipient_id')} → {s.get('status')} (msg {s.get('id','')[:12]})")
            return "ok", 200

        if not msgs:
            return "ok", 200

        msg      = msgs[0]
        msg_type = msg.get("type")

        if msg_type == "text":
            user_text = msg["text"]["body"]
        elif msg_type == "audio":
            media_id    = msg.get("audio", {}).get("id")
            audio_bytes = wa_download_media(media_id) if media_id else None
            if not audio_bytes:
                return "ok", 200
            if OPENAI_KEY:
                user_text = transcribe_audio(audio_bytes)
                if not user_text:
                    # Whisper falló — avisar al usuario y no quedar muda
                    from_phone = msg.get("from", "")
                    if from_phone:
                        wa_send(from_phone, "No escuché bien el audio 😅 ¿Me lo podés escribir?")
                    return "ok", 200
                print(f"[Audio transcripto] {user_text[:80]}")
            else:
                # Sin Whisper configurado — pedir que escriban
                from_phone = msg.get("from", "")
                if from_phone:
                    wa_send(from_phone, "Por ahora solo puedo leer mensajes de texto 😊 ¿Me contás qué buscás?")
                return "ok", 200
        else:
            print(f"[WA tipo ignorado] {msg_type} de {msg.get('from','?')}")
            return "ok", 200

        from_phone = msg["from"]
        print(f"[WA] {from_phone}: {user_text[:80]}")

        # (filtro de número propio desactivado — Santiago puede escribir para probar)

        wa_profile_name = value.get("contacts", [{}])[0].get("profile", {}).get("name", "")

        # Debounce: agrupa mensajes en ráfaga antes de responder
        with _pending_lock:
            if from_phone in _pending:
                _pending[from_phone]['timer'].cancel()
                _pending[from_phone]['texts'].append(user_text)
                # Guardar nombre si llegó en este mensaje
                if wa_profile_name and not _pending[from_phone].get('profile_name'):
                    _pending[from_phone]['profile_name'] = wa_profile_name
            else:
                _pending[from_phone] = {'texts': [user_text], 'profile_name': wa_profile_name}
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


# ── Digest cada 2 horas ────────────────────────────────────────────────────────

def build_digest(hours: int = 2) -> str:
    """Construye el resumen de actividad de las últimas N horas."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    sb = _sfre_client()
    res = sb.table("chat_leads").select("*").gte("last_message_at", cutoff).execute()
    leads = res.data or []
    if not leads:
        return ""

    calientes = [l for l in leads if l.get("sofia_paused")]
    activos   = [l for l in leads if not l.get("sofia_paused")]

    lines = ["📊 *Resumen Sofía — últimas 2hs*"]
    lines.append(f"💬 Conversaciones: {len(leads)}\n")

    if calientes:
        lines.append(f"🔥 *Leads calientes ({len(calientes)}) — esperan tu contacto:*")
        for l in calientes:
            name  = l.get("name") or "Sin nombre"
            phone = l.get("phone", "")
            msgs  = messages_get(l["id"], limit=10)
            last_user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "—")
            lines.append(f"• *{name}* (+{phone})\n  _{last_user[:80]}_")
        lines.append("")

    if activos:
        lines.append(f"💬 *Activos ({len(activos)}):*")
        for l in activos:
            name  = l.get("name") or "Sin nombre"
            phone = l.get("phone", "")
            msgs  = messages_get(l["id"], limit=10)
            last_user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "—")
            lines.append(f"• *{name}* (+{phone})\n  _{last_user[:70]}_")

    return "\n".join(lines)

def send_digest(hours: int = 2) -> None:
    try:
        msg = build_digest(hours=hours)
        if msg:
            tg_send(msg)
            print(f"[Digest] Enviado a Santiago ({hours}hs)")
        else:
            print(f"[Digest] Sin actividad en las últimas {hours}hs — omitido")
    except Exception as e:
        print(f"[Digest] Error: {e}")

@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json(silent=True) or {}
    msg  = data.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text    = msg.get("text", "").strip()
    if not text or chat_id != TELEGRAM_CHAT_ID:
        return "ok", 200
    threading.Thread(target=_handle_manager, args=[text], daemon=True).start()
    return "ok", 200

@app.route("/admin/digest", methods=["POST"])
def trigger_digest():
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    hours = int(request.get_json(silent=True).get("hours", 2))
    threading.Thread(target=send_digest, args=[hours], daemon=True).start()
    return jsonify({"ok": True, "hours": hours})

def _start_scheduler() -> None:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(timezone="America/Argentina/Buenos_Aires")
    scheduler.add_job(send_digest, "interval", hours=2, id="digest_2h")
    scheduler.start()
    print("[Scheduler] Digest cada 2hs iniciado")

# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Altavista Otero — Servidor Railway ===")
    print(f"Puerto: {PORT}")
    print(f"Sofía WhatsApp: {'lista' if WA_TOKEN and WA_PHONE_ID else 'sin credenciales WA'}")
    print(f"Anthropic: {'configurado' if ANTHROPIC_KEY else 'NO CONFIGURADO'}")
    print(f"Supabase sfre-web: {'OK' if SFRE_SUPABASE_URL else 'NO CONFIGURADO'}")
    _start_scheduler()
    app.run(host="0.0.0.0", port=PORT)
