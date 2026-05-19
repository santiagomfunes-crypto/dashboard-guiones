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

# WhatsApp Cloud API (Meta directo — usado como fallback)
WA_TOKEN      = os.environ.get("WHATSAPP_TOKEN", "")
WA_PHONE_ID   = os.environ.get("WHATSAPP_PHONE_ID", "")
WA_VERIFY     = os.environ.get("WHATSAPP_VERIFY_TOKEN", "altavista-sofia-2026")

# Wati BSP
WATI_API_URL   = os.environ.get("WATI_API_URL", "")
WATI_API_TOKEN = os.environ.get("WATI_API_TOKEN", "")

# Respond.io BSP (prioridad máxima cuando está configurado)
RESPOND_API_TOKEN  = os.environ.get("RESPOND_API_TOKEN", "")
RESPOND_CHANNEL_ID = int(os.environ.get("RESPOND_CHANNEL_ID", "500829"))

# Santiago — número WhatsApp (para detección de mensajes entrantes)
SANTIAGO_PHONE = os.environ.get("SANTIAGO_PHONE", "")

# Evolution API — notificaciones internas a Santiago (sin restricción 24hs)
EVOLUTION_URL      = os.environ.get("EVOLUTION_API_URL", "")
EVOLUTION_KEY      = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "santiago")

# Template de re-engagement para cuando la sesión de 24hs expiró
WATI_REENGAGEMENT_TEMPLATE = os.environ.get("WATI_REENGAGEMENT_TEMPLATE", "reengagement_altavista_01")

# Token secreto para validar que el webhook viene de Wati (no de cualquiera)
WATI_WEBHOOK_SECRET = os.environ.get("WATI_WEBHOOK_SECRET", "")

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

# Modelo de Sofía — overridable vía env var para cambiar sin redeploy.
# Por defecto Sonnet 4.6; si se llega al rate limit, set SOFIA_MODEL=claude-haiku-4-5-20251001 en Railway.
SOFIA_MODEL = os.getenv("SOFIA_MODEL", "claude-sonnet-4-6")


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

def _respond_send(phone_digits: str, text: str) -> None:
    """Envía un mensaje vía Respond.io API. Si el contacto no existe, lo crea primero."""
    phone_e164 = f"+{phone_digits}"
    payload = {"channelId": RESPOND_CHANNEL_ID, "message": {"type": "text", "text": text}}
    headers = {"Authorization": f"Bearer {RESPOND_API_TOKEN}", "Content-Type": "application/json"}
    resp = http_requests.post(
        f"https://api.respond.io/v2/contact/phone:{phone_e164}/message",
        json=payload, headers=headers, timeout=10,
    )
    if resp.status_code == 404:
        # Contacto no existe en Respond.io — crearlo y reintentar
        http_requests.post(
            f"https://api.respond.io/v2/contact/create_or_update/phone:{phone_e164}",
            json={}, headers=headers, timeout=10,
        )
        resp = http_requests.post(
            f"https://api.respond.io/v2/contact/phone:{phone_e164}/message",
            json=payload, headers=headers, timeout=10,
        )
    print(f"[Respond.io send → {phone_e164}] {resp.status_code}")
    if not resp.ok:
        body = resp.text[:500]
        print(f"[Respond.io ERROR] {resp.status_code} — {body}")
        raise RuntimeError(f"Respond.io API error {resp.status_code}: {body}")


def wa_send(to: str, text: str, fallback_name: str = "") -> None:
    phone = re.sub(r"[^\d]", "", to)
    if WATI_API_URL and WATI_API_TOKEN:
        # Wati BSP — messageText va como query param
        resp = http_requests.post(
            f"{WATI_API_URL.rstrip('/')}/api/v1/sendSessionMessage/{phone}",
            params={"messageText": text},
            headers={"Authorization": f"Bearer {WATI_API_TOKEN}"},
            timeout=10,
        )
        print(f"[Wati send → {phone}] {resp.status_code}")
        if not resp.ok:
            body = resp.text[:500]
            print(f"[Wati ERROR] {resp.status_code} — {body}")
            # Sesión de 24hs expirada → intentar con template de re-engagement
            if "131047" in body or resp.status_code == 400:
                name = fallback_name or "ahí"
                sent = _wati_send_template(phone, WATI_REENGAGEMENT_TEMPLATE, [
                    {"name": "1", "value": name}
                ])
                if sent:
                    print(f"[Wati] Re-engagement template enviado a {phone}")
                    return
            raise RuntimeError(f"Wati API error {resp.status_code}: {body}")
    elif WA_TOKEN and WA_PHONE_ID:
        # Fallback: Meta Cloud API directa
        resp = http_requests.post(
            f"https://graph.facebook.com/v20.0/{WA_PHONE_ID}/messages",
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
            headers={"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"},
            timeout=10,
        )
        print(f"[WhatsApp send → {to}] {resp.status_code}")
        if not resp.ok:
            body = resp.text[:500]
            print(f"[WhatsApp ERROR] {resp.status_code} — {body}")
            raise RuntimeError(f"WhatsApp API error {resp.status_code}: {body}")
    else:
        raise RuntimeError("[WhatsApp] Sin credenciales — configurar RESPOND_API_TOKEN, WATI_API_URL/WATI_API_TOKEN, o WHATSAPP_TOKEN/WHATSAPP_PHONE_ID")

def _classify_lead_from_state(lead_state_text: str, lead_notas: str, last_reply: str, is_urgent: bool, is_new: bool) -> dict:
    """Construye el diccionario completo de atributos para Wati basado en el estado del lead.
    Esto centraliza la clasificación para que cada lead tenga la mayor cantidad de campos posible."""
    attrs = {}

    # Combinar todas las fuentes de info
    full = (lead_state_text + "\n" + lead_notas + "\n" + last_reply).lower()

    # Temperatura
    if is_urgent or "qualified" in last_reply.lower() or "paso el whatsapp de santiago" in last_reply.lower():
        attrs["temperatura"] = "caliente"
        attrs["etiqueta"] = "🔥 caliente"
        attrs["lead_stage"] = "Qualified"
    elif is_new:
        attrs["temperatura"] = "nuevo"
        attrs["etiqueta"] = "🆕 nuevo"
        attrs["lead_stage"] = "New lead"
    else:
        attrs["temperatura"] = "tibio"
        attrs["etiqueta"] = "🟡 tibio"
        attrs["lead_stage"] = "Contacted"

    # Tipo de lead
    if any(k in full for k in ["tasación", "tasacion", "vender mi", "quiero vender"]):
        attrs["tipo_lead"] = "tasacion"
    elif any(k in full for k in ["inversor", "comprar para alquilar", "renta", "rentabilidad", "invertir"]):
        attrs["tipo_lead"] = "inversor"
    elif any(k in full for k in ["busco alquilar", "quiero alquilar", "necesito alquilar"]):
        attrs["tipo_lead"] = "inquilino"
    elif any(k in full for k in ["para vivir", "para habitarlo", "para mi familia"]):
        attrs["tipo_lead"] = "comprador_vivir"
    else:
        attrs["tipo_lead"] = "comprador"

    # Presupuesto USD — buscar primero en lead_state (más confiable), después en notas
    m = re.search(r'USD\s*([\d,.]+)', lead_state_text + " " + lead_notas)
    if m:
        try:
            attrs["presupuesto_usd"] = m.group(1).replace(",", "").replace(".", "")
        except Exception:
            pass
    elif re.search(r'hasta\s+usd\s*100', full):
        attrs["presupuesto_usd"] = "100000"

    # Dormitorios
    if "2 dormitorios" in full or "dos dormitorios" in full:
        attrs["dormitorios"] = "2"
    elif "1 dormitorio" in full or "un dormitorio" in full or "1_dormitorio" in full:
        attrs["dormitorios"] = "1"
    elif "3 dormitorios" in full:
        attrs["dormitorios"] = "3"

    # Zona
    if "centro" in full:
        attrs["zona"] = "centro"

    # Propiedad de interés (mapear del notas)
    for prop in ["Garibaldi 431", "San Lorenzo 420", "Roca 36", "Chacabuco 977", "Constitución 862", "Alberdi 348", "Guatemala 1098", "Sarmiento 1200", "Paz 341"]:
        if prop.lower() in (lead_notas + " " + last_reply).lower():
            attrs["propiedad_interes"] = prop
            break

    # Plazo
    if any(k in full for k in ["urgente", "este mes", "lo antes posible", "1 a 3 meses", "1_a_3_meses"]):
        attrs["plazo"] = "corto"
    elif any(k in full for k in ["evaluando", "más adelante", "sin apuro", "3 a 6 meses", "3_a_6_meses"]):
        attrs["plazo"] = "evaluando"

    # Forma de pago
    if any(k in full for k in ["crédito", "credito", "uva", "hipotecario", "con banco"]):
        attrs["forma_pago"] = "credito_hipotecario"
    elif any(k in full for k in ["contado", "efectivo", "cash"]):
        attrs["forma_pago"] = "contado"
    elif "cuotas" in full or "financ" in full:
        attrs["forma_pago"] = "financiacion"

    # Crédito hipotecario flag (importante para que no le ofrezcan Garibaldi 431)
    if attrs.get("forma_pago") == "credito_hipotecario":
        attrs["alerta_credito"] = "si"

    return attrs

def wati_update_contact_attrs(phone: str, attrs: dict) -> None:
    """Actualiza atributos del contacto en Wati CRM. Corre en background thread."""
    if not WATI_API_URL or not WATI_API_TOKEN:
        return
    phone = re.sub(r"[^\d]", "", phone)
    params = [{"name": k, "value": str(v)} for k, v in attrs.items()]
    try:
        resp = http_requests.post(
            f"{WATI_API_URL.rstrip('/')}/api/v1/updateContactAttributes/{phone}",
            json={"customParams": params},
            headers={"Authorization": f"Bearer {WATI_API_TOKEN}", "Content-Type": "application/json"},
            timeout=10,
        )
        print(f"[Wati attrs → {phone}] {resp.status_code} {list(attrs.keys())}")
    except Exception as e:
        print(f"[Wati attrs error] {e}")

def _evolution_send(phone: str, text: str) -> bool:
    """Envía mensaje directo a Santiago vía Evolution API (sin restricción de 24hs)."""
    if not EVOLUTION_URL or not EVOLUTION_KEY or not EVOLUTION_INSTANCE:
        return False
    try:
        resp = http_requests.post(
            f"{EVOLUTION_URL.rstrip('/')}/message/sendText/{EVOLUTION_INSTANCE}",
            json={"number": phone, "text": text},
            headers={"apikey": EVOLUTION_KEY, "Content-Type": "application/json"},
            timeout=10,
        )
        print(f"[Evolution → {phone}] {resp.status_code}")
        return resp.ok
    except Exception as e:
        print(f"[Evolution error] {e}")
        return False

def _wati_send_template(phone: str, template_name: str, params: list, broadcast_name: str = "") -> bool:
    """Envía un template de Wati. Útil cuando la sesión de 24hs está cerrada."""
    if not WATI_API_URL or not WATI_API_TOKEN:
        return False
    bname = broadcast_name or f"auto_{template_name}"
    try:
        resp = http_requests.post(
            f"{WATI_API_URL.rstrip('/')}/api/v1/sendTemplateMessage",
            params={"whatsappNumber": phone},
            json={
                "template_name": template_name,
                "broadcast_name": bname,
                "parameters": params,
            },
            headers={"Authorization": f"Bearer {WATI_API_TOKEN}", "Content-Type": "application/json"},
            timeout=10,
        )
        body_txt = resp.text[:200]
        print(f"[Wati template {template_name} → {phone}] {resp.status_code} {body_txt}")
        return resp.ok
    except Exception as e:
        print(f"[Wati template error] {e}")
        return False

def wa_send_internal(text: str) -> None:
    """Notifica a Santiago. Prueba canales en orden hasta que uno funcione."""
    if not SANTIAGO_PHONE:
        print("[Internal] SANTIAGO_PHONE no configurado")
        return
    phone = _normalize_phone(SANTIAGO_PHONE)
    clean = (text
        .replace("\\.", ".").replace("\\(", "(").replace("\\)", ")")
        .replace("\\-", "-").replace("\\!", "!").replace("\\=", "=")
    )
    # 1. Evolution API — sin restricción de 24hs (si está configurado)
    if _evolution_send(phone, clean):
        return
    # 2. Wati session message — puede fallar si la ventana de 24hs expiró
    if WATI_API_URL and WATI_API_TOKEN:
        try:
            resp = http_requests.post(
                f"{WATI_API_URL.rstrip('/')}/api/v1/sendSessionMessage/{phone}",
                params={"messageText": clean},
                headers={"Authorization": f"Bearer {WATI_API_TOKEN}"},
                timeout=10,
            )
            print(f"[Internal Wati → {phone}] {resp.status_code}")
            if resp.ok:
                return
            body = resp.text[:300]
            print(f"[Internal Wati session ERROR] {resp.status_code} — {body}")
        except Exception as e:
            print(f"[Internal Wati session error] {e}")
        # 3. Fallback: template de alerta si existe, si no usa reengagement con resumen en param {{1}}
        alert_template = os.environ.get("SANTIAGO_ALERT_TEMPLATE", "")
        if alert_template:
            # Template dedicado para Santiago — body es {{1}} con el texto completo
            sent = _wati_send_template(phone, alert_template, [{"name": "1", "value": clean[:1000]}],
                                       broadcast_name="alerta_santiago_auto")
            if sent:
                print(f"[Internal] Alert template '{alert_template}' enviado a Santiago")
                return
        # 4. Último recurso: reengagement template con resumen en el campo nombre
        summary_line = clean.split("\n")[0][:60]
        sent = _wati_send_template(phone, WATI_REENGAGEMENT_TEMPLATE,
                                   [{"name": "1", "value": summary_line}],
                                   broadcast_name="alerta_interna_fallback")
        if sent:
            print(f"[Internal] Reengagement fallback enviado a Santiago con: {summary_line}")
            return
        print(f"[Internal] Todos los canales fallaron — notificación logueada: {clean[:200]}")
    raise RuntimeError("[Internal] Sin canal configurado — EVOLUTION_API_URL o WATI_API_URL requeridos")

def tg_send(text: str) -> None:
    wa_send_internal(text)

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
    # Toma el primer número en formato argentino (115.000 = 115000) o entero simple
    m = re.search(r'\d{1,3}(?:\.\d{3})+|\d+', str(s))
    if not m:
        return None
    return float(m.group().replace('.', ''))

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
        # ROI desactivado hasta aprobación de Santiago
        # if p.get("alquiler_estimado"):
        #     alquiler = _parse_num(p["alquiler_estimado"])
        #     precio   = _parse_num(p["precio"])
        #     if alquiler and precio and precio > 0:
        #         roi = (alquiler * 12 / precio) * 100
        #         parts.append(f"ROI anual estimado: {roi:.1f}%")
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

def _extract_lead_state(history: list) -> str:
    """Extrae hechos confirmados de la conversación para anclar contexto en cada llamada."""
    if not history:
        return ""
    user_msgs = " ".join(m["content"] for m in history if m["role"] == "user").lower()
    lines = []

    # Presupuesto — detectar moneda explícita; si dice solo número, NO asumir USD
    m_usd_explicit = re.search(
        r'(\d{2,3}(?:[.,]\d{3})?)\s*(?:k\b|mil\s*(?:dolares|dólares|usd)|usd|u\$s|dólares|dolares)',
        user_msgs,
    )
    m_ars = re.search(r'(\d{2,4})\s*mil\s*pesos\b|(\d{4,7})\s*pesos\b', user_msgs)
    if m_usd_explicit:
        raw = m_usd_explicit.group(1).replace(".", "").replace(",", "")
        try:
            budget = int(raw)
            if budget < 1000:
                budget *= 1000
            lines.append(
                f"- Presupuesto declarado: USD {budget:,}. NUNCA ofrecer nada por encima sin antes preguntar si puede estirar."
            )
        except ValueError:
            pass
    elif m_ars:
        lines.append("- ALERTA: lead mencionó presupuesto en PESOS. Confirmar si es para alquiler mensual o compra antes de avanzar.")

    # Perfil — comprar para alquilar es inversor; "para alquilar" solo es inquilino con verbos claros
    if any(k in user_msgs for k in ["comprar para alquilar", "para alquilarlo", "para alquilarla", "para rentarlo", "inversión", "inversion", "invertir", "rentabilidad", "como inversor"]):
        lines.append("- Perfil confirmado: inversor (quiere comprar para alquilar/rentar)")
    elif any(k in user_msgs for k in ["para vivir yo", "para vivir", "para habitarlo", "para mi familia", "para nosotros", "para estar yo", "vivir vos"]):
        lines.append("- Perfil confirmado: comprador para vivir")
    elif any(k in user_msgs for k in ["busco alquilar", "quiero alquilar", "necesito alquilar"]):
        lines.append("- Perfil confirmado: inquilino (busca lugar para alquilar)")

    # Dormitorios
    if any(k in user_msgs for k in ["2 dormitorios", "dos dormitorios", "2 ambientes", "dos ambientes"]):
        lines.append("- Dormitorios buscados: 2")
    elif any(k in user_msgs for k in ["1 dormitorio", "un dormitorio", "1 ambiente", "un ambiente"]):
        lines.append("- Dormitorios buscados: 1")
    elif "3 dormitorios" in user_msgs or "tres dormitorios" in user_msgs:
        lines.append("- Dormitorios buscados: 3")

    # Zona
    if "centro" in user_msgs:
        lines.append("- Zona preferida: centro de Tandil")
    for calle in ["garibaldi", "chacabuco", "san lorenzo", "roca", "constitución", "constitucion", "alberdi", "guatemala", "sarmiento", "paz"]:
        if calle in user_msgs:
            lines.append(f"- Mencionó interés en: {calle.capitalize()}")
            break

    # Cochera
    if any(k in user_msgs for k in ["con cochera", "necesito cochera", "tiene que tener cochera", "cochera obligatoria"]):
        lines.append("- Requiere cochera")
    elif "sin cochera" in user_msgs or "no necesito cochera" in user_msgs:
        lines.append("- No requiere cochera")

    # Crédito hipotecario (ALERTA)
    if any(k in user_msgs for k in ["crédito", "credito", "uva", "préstamo", "prestamo", "con banco", "hipotecario", "apto credito", "apto crédito"]):
        lines.append("- ALERTA: lead mencionó crédito hipotecario. PROHIBIDO ofrecer Garibaldi 431.")

    # Plazo
    if any(k in user_msgs for k in ["urgente", "lo antes posible", "este mes"]):
        lines.append("- Plazo: corto / urgente")
    elif any(k in user_msgs for k in ["evaluando", "más adelante", "sin apuro"]):
        lines.append("- Plazo: sin urgencia (evaluando)")

    return "\n".join(lines)


def sofia_system_prompt() -> str:
    props = properties_context()
    return f"""<identidad>
Sos Sofía, secretaria de Santiago Funes, corredor inmobiliario en Tandil.
Tu trabajo es atender consultas por WhatsApp, entender qué busca el lead, mostrarle la propiedad correcta de la cartera, y derivarlo a Santiago cuando muestre intención real de avanzar.
Si te preguntan si sos IA o robot, respondé exactamente: "Para nada, soy Sofía, la secretaria de Santiago."
</identidad>

<reglas_absolutas>
Estas 7 reglas no se rompen nunca:

1. UNA PREGUNTA POR MENSAJE. Una sola. Nunca dos. Única excepción: "¿es para vivir o para invertir?".

2. NO REPETIR PREGUNTAS YA RESPONDIDAS. Si el lead dijo perfil, zona, presupuesto, plazo, dormitorios o forma de pago — anclá ese dato y NUNCA lo vuelvas a preguntar, aunque la respuesta haya sido implícita o parcial.

3. RESPONDER PRIMERO, PREGUNTAR DESPUÉS. Si el lead pregunta algo, contestá eso primero. Después tu pregunta de seguimiento, si corresponde. Si no tenés el dato: "Ese dato te lo confirmo." y punto, sin agregar otra pregunta.

4. PRESUPUESTO ES TECHO ABSOLUTO. Si el lead declaró presupuesto, NUNCA ofrezcas algo por encima. Si no hay nada en su rango: decí "En ese rango no tenemos. ¿Podés estirar un poco?" y esperá respuesta.

5. UNA PROPIEDAD POR MENSAJE — EXCEPTO MENÚ. Mostrá UNA propiedad por mensaje. Solo podés mostrar un menú de hasta 5 opciones cuando: el lead pidió alternativas explícitas Y vos ya tenés perfil + presupuesto + dormitorios + zona o forma de pago.

6. GARIBALDI 431 + CRÉDITO HIPOTECARIO = INCOMPATIBLE. Si el lead menciona crédito UVA, hipotecario o "con banco", NO ofrezcas Garibaldi 431. Sin excepciones.

7. NO PROPONER VISITA sin señal real de avance. No digas "¿cuándo te viene bien para verla?" hasta que el lead lo pida o muestre intención clara de avanzar (reservar, seña, escritura).
</reglas_absolutas>

<flujo_por_escenario>
Identificá en qué escenario estás antes de responder. Hay tres:

ESCENARIO A — FORM CON PROPIEDAD IDENTIFICADA
Las notas mencionan una propiedad específica (Roca 36, Garibaldi 431, Chacabuco 977, San Lorenzo 420, etc.).

Primer mensaje (modelo):
"Hola [Nombre], soy Sofía, la asistente de Santiago. Vi que te interesó [Propiedad], [una frase corta de qué es]. Lo podés ver acá: [URL]. ¿Lo estás pensando para vivir o como inversión?"

ESCENARIO B — FORM SIN PROPIEDAD PERO CON DATOS
Las notas tienen presupuesto y/o dormitorios y/o objetivo, pero no propiedad específica.

NUNCA preguntes "¿por cuál propiedad o proyecto te llegó el formulario?". Eso espanta. En su lugar: usá los datos del form para PROPONER DIRECTO la propiedad de la cartera que mejor calce, con link y precio. Después UNA pregunta de avance.

Ejemplo — form dice "1 dorm + hasta USD 100.000 + resguardo de capital":
"Hola [Nombre], soy Sofía, la asistente de Santiago. Vi tu formulario. Para 1 dormitorio hasta USD 100.000 con foco en resguardo de capital, te paso una opción que calza bien: Alberdi 348, 1 dorm con cochera. Lo podés ver acá: [URL]. ¿Te interesa esta o querés que te muestre alternativas?"

Si la única pregunta abierta es zona o forma de pago, podés preguntar eso después de proponer (no antes).

ESCENARIO C — SIN FORM
Lead escribió directo a WhatsApp sin pasar por formulario.

Primer mensaje:
"Hola, soy Sofía, la asistente de Santiago. Trabajamos con propiedades en Tandil — compra, inversión y alquiler. ¿Qué estás buscando?"

Después conducís con UNA pregunta por turno hasta tener perfil + presupuesto + dormitorios o zona — ahí mostrás propiedad.
</flujo_por_escenario>

<defaults_cuando_dudas>
Cuando el lead no aclara, asumí:

- VIVIR por defecto, no inversor. La palabra "rango_de_inversión" en el form es el label del campo de Meta Ads, NO una declaración de intención del lead. Si dice "comprar" sin más, asumí vivir.
- "Comprar para alquilar" = inversor. "Buscar para alquilar" / "necesito alquilar" / "quiero alquilar algo" = inquilino busca lugar.
- Si el lead dice un número solo ("400", "200"), confirmá moneda antes de avanzar: "¿Son 400.000 USD o 400 mil pesos?". NUNCA asumas USD automáticamente.
- Si dijo dormitorios en el form pero no encontrás en su rango: decí que en ese rango no hay y ofrecé estirar. NO le metas otra tipología sin antes preguntar.
</defaults_cuando_dudas>

<derivar_a_santiago>
Solo derivás cuando hay señal REAL de avance:
- Pide ver la propiedad ("¿cuándo puedo ir?", "¿podemos coordinar visita?")
- Pregunta cómo reservar, cuánto de seña, escritura, documentación
- Eligió una opción específica y pregunta detalles para avanzar
- Quiere hacer oferta o negociar

NO son señales de avance: "me interesa", "mandame info", "lo voy a pensar", llenar formulario, preguntar precio o fotos.

Frase exacta para derivar (no la modifiques):
"Te paso el WhatsApp de Santiago: +54 9 2494 20-9464. Le mando un resumen de lo que charlamos así te tiene contexto antes de hablar."

Después de esa frase, no agregues nada más en ese mensaje.

Caso TASACIÓN o VENTA: si el lead quiere vender o tasar su propiedad, derivá directo con:
"Perfecto. Le paso los datos a Santiago y él se va a comunicar con vos para coordinar la tasación."
</derivar_a_santiago>

<tono_y_estilo>
Mensajes cortos: 2-4 líneas por mensaje. Texto plano. Sin markdown ni negritas.
Voseo rioplatense: querés, podés, tenés, mirá, dale, claro, perfecto, entiendo, avisame, sin problema.
Nunca tuteo español: tú, quieres, puedes, tienes, para ti.

NO USAR NUNCA: buenísimo, bárbaro, genial, jaja, jeje, ¿nos charlamos?, ¿hablamos?, ¿cuándo te viene bien para hablar?, agendamos una llamada, te cuento algunas, te paso algunas opciones, te dejo las opciones, mirá tengo dos opciones, mirá tengo varias opciones, re agradezco.

Emojis: cero por default. Si usás uno, que sea muy natural y nunca más de uno por mensaje.

Cuando ofrezcas un menú de propiedades, separá cada opción con un salto de línea simple. Formato:
"Te paso las opciones que mejor calzan:
1) [Propiedad] — [datos clave], USD [precio]. [URL]
2) [...]
3) [...]
¿Cuál te tira más?"

Nunca uses intros tipo "Te dejo las opciones" o "Son las siguientes".
</tono_y_estilo>

<manejo_objeciones>
"Está caro": "Entiendo. Depende mucho de qué estés comparando: ubicación, estado y metros. ¿Qué es lo que más te importa?"
"Lo voy a pensar": "Claro, sin apuro. Si surge algo, avisame."
"Vi algo más barato": "Puede ser. ¿Querés que te cuente qué tiene esta de distinto?"
"No tengo el dinero ahora": "Entiendo. ¿Es para más adelante o tenés un tiempo estimado?"
"¿El precio es negociable?": "El precio puede tener algo de margen según unidad y forma de pago. Te lo consulto y te confirma."
Nunca digas que todos los precios tienen margen.
</manejo_objeciones>

<datos_faltantes>
Si te falta un dato concreto (m² exactos, expensas, fecha exacta de entrega, dirección exacta de una unidad específica):
Respondé con UNA de estas frases (rotá entre ellas, no repitas la misma):
- "Ese dato te lo confirmo."
- "No lo tengo a mano, te lo paso hoy."
- "Ese detalle varía por unidad, lo chequeamos antes de avanzar."

Cuando uses una de estas frases, ese mensaje TERMINA AHÍ. No agregues otra pregunta en el mismo mensaje.

Nunca inventes precios, m², expensas, ROI, renta, fecha de entrega, financiación, dirección exacta ni nada que no esté en Supabase o en este prompt.
</datos_faltantes>

<links>
Cada vez que nombres una propiedad y tengas link cargado en Supabase, incluí la URL completa en ese mismo mensaje.
Si no tenés link cargado, no inventes URL. Pasá la info disponible y seguí.
</links>

<credito_hipotecario>
Si el lead menciona crédito UVA, hipotecario, bancario o "con banco":
- Garibaldi 431: NO ofrecer. Es incompatible.
- Otras: "Te confirmo si aplica para crédito antes de avanzar."
- Preguntá: "¿Tenés el crédito aprobado o todavía en trámite?"
- Si aprobado: el monto del crédito = su presupuesto real, tratalo como comprador definido.
- Si en trámite: ofrecé opciones y preguntá cuánto estima que le aprobarán.
- Nunca prometás que "entra en crédito" sin confirmarlo con Santiago.
</credito_hipotecario>

<urgencia>
Solo usá urgencia si hay señal real de avance (quiere reservar, coordinó visita, preguntó por seña).
Frase: "Esta unidad tiene bastante movimiento. Si te interesa reservarla, mejor no demorarlo mucho."
Una sola vez por conversación. Nunca inventes urgencia si no hay señal real.
</urgencia>

<estado_construccion>
SOLO estas dos propiedades están en construcción (no terminadas):
- Roca 36 — fideicomiso al costo en pozo. Entrega ~24 meses.
- Chacabuco 977 / Garibaldi 451 — mismo edificio esquina, dos direcciones. En construcción.

TODAS las demás (Garibaldi 431, San Lorenzo 420, Alberdi 348, Constitución 862, Guatemala 1098, Sarmiento 1200, Paz 341, etc.) están TERMINADAS y disponibles para entregar.

Si preguntan "¿está terminado?": responder sí para cualquiera menos Roca 36 y Chacabuco 977.
</estado_construccion>

<propiedades_clave>
GARIBALDI 431 — 1 dorm, centro Tandil, 4 pisos. SOLO 1 dormitorio (nunca digas 2). Sin cochera USD 115.000, con cochera USD 125.000. Tipología pasante (52 m²) es diferencial para inversores. Renta estimada USD 550/mes. ROI 6,3%. NO apta para crédito hipotecario. Propiedad PRIORITARIA: priorizala para compradores al contado e inversores.

CHACABUCO 977 / GARIBALDI 451 — Mismo edificio esquina, dos direcciones. EN CONSTRUCCIÓN. 2 dorm frente con cochera 70 m², 2 baños, USD 175.000. 1 dorm contrafrente: 45 m² + balcón, USD 115.000 sin cochera / USD 125.000 con cochera.

ROCA 36 — Fideicomiso al costo en pozo. Esquina Roca y Avellaneda. PB + 3 pisos, ascensor. 1 dorm 52,90 m² + balcón. USD 102.500. Cochera USD 9.000. Locales PB desde USD 66.000. Esquema: reserva USD 5.000 + 30% anticipo + cuotas pesos CAC. Entrega ~24 meses. Desarrollador Estudio Pascua.

SAN LORENZO 420 — A estrenar (terminado). Calefacción central, ascensor, portero, terraza. 2° piso RESERVADO (ambas unidades vendidas, no ofrecer). Disponible: 3° piso frente 2 dorm con cochera 77 m², 2 baños, USD 175.000, renta USD 638/mes. 1° piso contrafrente 1 dorm sin cochera 54 m² USD 120.000, renta USD 514/mes. San Lorenzo es calle, no barrio.

Otras propiedades cargadas en Supabase (datos principales abajo): Sarmiento 1200, Alberdi 348, Guatemala 1098, Paz 341. (Constitución 862: VENDIDA, no ofrecer.)

Roca, Avellaneda, Sarmiento, Constitución, Uriburu, Garibaldi, Chacabuco, San Lorenzo son CALLES de Tandil, no barrios.
</propiedades_clave>

<orden_recomendacion>
Para compra de 1 dorm con presupuesto hasta USD 100.000 (vivir o invertir), prioridad:
1) Garibaldi 431, 4to piso al frente
2) Alberdi 348
3) Guatemala 1098

Mostrá UNA según disponibilidad de Supabase. Si una no está, pasá a la siguiente. NUNCA las mencionés todas en un mismo mensaje (salvo menú explícito según regla 5).

Para 2 dormitorios hasta USD 100.000: no hay nada en cartera; decilo directo y proponé estirar.
</orden_recomendacion>

<datos_oficiales>
Santiago Funes — corredor inmobiliario en Tandil. NO digas arquitecto, desarrollador, martillero ni constructor.
Juan Ignacio Otero — Martillero Público responsable, Mat. 1966, Departamento Judicial Azul.
Oficina: Av. Avellaneda 1140, Tandil.
WhatsApp Santiago: +54 9 2494 20-9464.
</datos_oficiales>

<jerarquia_de_datos>
Supabase es la fuente principal para precio, disponibilidad, m², links, renta, ROI, entrega, forma de pago.
Si Supabase contradice los datos de <propiedades_clave>, manda Supabase.
Si Supabase no confirma disponibilidad: "Lo tengo como referencia, pero te confirmo disponibilidad actual."
Si una propiedad figura como reservada, vendida o no disponible: NO la ofrezcas.
Si preguntan por una propiedad que no aparece en Supabase ni en los datos clave: "No la tengo cargada acá. Si querés, lo revisamos para confirmarte."
Nunca muestres observaciones internas, nombres de campos, placeholders ni corchetes al lead.
</jerarquia_de_datos>

<propiedades_disponibles_supabase>
{props}
</propiedades_disponibles_supabase>

<objetivo>
El objetivo NO es cerrar la operación por WhatsApp. Es entender qué busca el lead, mostrarle la propiedad correcta, evitar errores de información, y derivar a Santiago cuando hay interés real.
Respondé siempre como Sofía: tono humano, claro, breve, comercial y natural.
</objetivo>"""


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
    is_first_message = len(history) == 0

    # Anclar hechos confirmados de la conversación para evitar context drift
    # Anclar hechos confirmados desde el PRIMER turno del lead (no esperar a 3+)
    if history:
        lead_state = _extract_lead_state(history)
        if lead_state:
            system += f"\n\n<estado_confirmado_del_lead>\nEstos hechos ya fueron confirmados por el lead. NO los vuelvas a preguntar. Respetarlos es obligatorio:\n{lead_state}\n</estado_confirmado_del_lead>"

    if lead_notas:
        system += (
            f"\n\n<contexto_del_form>\n{lead_notas}\n</contexto_del_form>\n"
            "INSTRUCCIONES sobre este contexto:\n"
            "- Estos datos YA los respondió el lead en el formulario. NO los repreguntes.\n"
            "- NUNCA preguntes 'por cuál propiedad te llegó el formulario' — eso espanta. Si no hay propiedad identificada, usá los datos para PROPONER DIRECTO la propiedad de la cartera que mejor calce con presupuesto + dormitorios + objetivo del lead.\n"
            "- Si solo tenés presupuesto y dormitorios, ya alcanza para proponer. Después preguntás UNA cosa (zona, forma de pago) para refinar.\n"
            "- 'rango_de_inversión' es el label del campo de Meta Ads, no significa que el lead sea inversor. Solo asumí inversor si el lead dice explícitamente 'invertir', 'para alquilar', 'rentar', 'inversión'."
        )
    elif is_first_message:
        system += (
            "\n\n<primer_contacto_sin_form>\n"
            "Este lead escribió directo por WhatsApp sin formulario. Tu primer mensaje DEBE:\n"
            "1. Incluir 'soy Sofía, la asistente de Santiago'\n"
            "2. Mencionar brevemente la inmobiliaria (\"trabajamos con propiedades en Tandil\")\n"
            "3. Terminar con una pregunta abierta: '¿Qué estás buscando?' o '¿Por cuál propiedad escribís?'\n"
            "NO conversés casual como amigo. Sos secretaria profesional.\n"
            "</primer_contacto_sin_form>"
        )
    if tasacion:
        system += (
            "\n\n<instruccion_tasacion>\n"
            "Este lead quiere vender o tasar su propiedad. Respondé exactamente:\n"
            "'Perfecto. Le paso los datos a Santiago y él se va a comunicar con vos para coordinar la tasación.'\n"
            "Sin emojis. Sin más preguntas. Sin pedidos de datos adicionales.\n"
            "</instruccion_tasacion>"
        )
    elif escalate:
        system += (
            "\n\n<instruccion_derivar>\n"
            "Este lead está mostrando interés concreto de avance. Respondé brevemente su pregunta o comentario, y cerrá el mensaje con exactamente esta frase:\n"
            "'Te paso el WhatsApp de Santiago: +54 9 2494 20-9464. Le mando un resumen de lo que charlamos así te tiene contexto antes de hablar.'\n"
            "Sin emojis al final. Sin agregar más preguntas después de esa frase.\n"
            "</instruccion_derivar>"
        )
    client = _anthropic_client()
    response = client.messages.create(
        model=SOFIA_MODEL,
        max_tokens=400,
        system=system,
        messages=messages,
        timeout=25.0,
    )
    _log_api_usage(
        model=SOFIA_MODEL,
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
    # Haiku confunde voseo y genera "soy Sos Sofía" — corregir
    text = re.sub(r'\bsoy\s+[Ss]os\s+', 'soy ', text)
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
        model=SOFIA_MODEL,
        max_tokens=500,
        system=f"""Sos Sofía, la secretaria de Santiago Funes.
Santiago te escribe directo para preguntarte sobre el estado de los leads. Respondele de forma clara, breve y útil.
Podés responder preguntas como "¿cómo va?", "¿qué está pasando?", "¿quién es el más caliente?", "¿qué quiere Fulano?", etc.
Hoy es {now} (hora Argentina).

ESTADO ACTUAL DE LOS LEADS:
{leads_ctx}
Respondé en español rioplatense, sin markdown. Sé directa y concisa.""",
        messages=[{"role": "user", "content": user_text}],
    )
    _log_api_usage(
        model=SOFIA_MODEL,
        tokens_input=response.usage.input_tokens,
        tokens_output=response.usage.output_tokens,
        cost_usd=(response.usage.input_tokens * _HAIKU_INPUT_COST_PER_TOKEN
                  + response.usage.output_tokens * _HAIKU_OUTPUT_COST_PER_TOKEN),
    )
    return response.content[0].text

def _handle_manager(user_text: str) -> None:
    cmd = user_text.strip().lower()

    # Comando: "reactivar 5491112345" o "sofia on 5491112345" → reactivar bot para ese lead
    if cmd.startswith(("reactivar", "sofia on", "activar sofia")):
        phone_match = re.search(r'\d{10,}', user_text)
        if phone_match:
            phone = phone_match.group()
            try:
                sb = _sfre_client()
                res = sb.table("chat_leads").select("id,name").eq("phone", phone).execute()
                if res.data:
                    lead_set_paused(res.data[0]["id"], False)
                    name = res.data[0].get("name") or phone
                    tg_send(f"Sofía reactivada para {name} ({phone})")
                else:
                    tg_send(f"Lead {phone} no encontrado en la base.")
            except Exception as e:
                tg_send(f"Error reactivando: {e}")
        else:
            tg_send("Indicá el número. Ejemplo: reactivar 5492494123456")
        return

    # Comando: "pausar 5491112345" → pausar manualmente
    if cmd.startswith("pausar"):
        phone_match = re.search(r'\d{10,}', user_text)
        if phone_match:
            phone = phone_match.group()
            try:
                sb = _sfre_client()
                res = sb.table("chat_leads").select("id,name").eq("phone", phone).execute()
                if res.data:
                    lead_set_paused(res.data[0]["id"], True)
                    name = res.data[0].get("name") or phone
                    tg_send(f"Sofía pausada para {name} ({phone})")
                else:
                    tg_send(f"Lead {phone} no encontrado.")
            except Exception as e:
                tg_send(f"Error pausando: {e}")
        else:
            tg_send("Indicá el número. Ejemplo: pausar 5492494123456")
        return

    # Default: informe de leads
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
    tg_send(
        f"🏠 *Tasación — propietario quiere vender*\n\n"
        f"*{name}* (+{phone})\n"
        f"Dice: {user_text[:200]}\n\n"
        f"Sofía pausó. Escribile: https://wa.me/{phone}"
    )

def detect_urgency(user_text: str, history: list) -> tuple:
    """Clasifica si el lead muestra señales de alta intención. Retorna (is_urgent, summary)."""
    import json as _json
    messages = history[-6:] + [{"role": "user", "content": user_text}]
    try:
        client = _anthropic_client()
        response = client.messages.create(
            model=SOFIA_MODEL,
            max_tokens=150,
            system="""Sos un clasificador de leads para un chatbot inmobiliario.
Analizá el último mensaje del lead y la conversación reciente.
Respondé SOLO JSON válido con dos campos:
- "urgent": true SOLO si el lead cumple al menos UNO de estos criterios concretos:
  * Quiere ver la propiedad (menciona visita, horario, "¿cuándo puedo ir?", "¿podemos coordinar?")
  * Pregunta cómo reservar, cuánto de seña, cómo firmar, cómo avanzar con la compra
  * Dice explícitamente que quiere comprar/invertir y tiene presupuesto definido en números ("tengo 80 mil", "dispongo de 100k")
  * Pregunta por documentación legal, escritura, fideicomiso con intención de avanzar
  NO es urgente: "me interesa", "mandame más info", preguntar precio, preguntar forma de pago general, pedir el link, decir que va a pensarlo.
- "summary": en una oración qué busca y por qué es urgente (para notificar al agente). Vacío si no es urgente.
Si no hay urgencia clara: {"urgent": false, "summary": ""}""",
            messages=messages,
        )
        _log_api_usage(
            model=SOFIA_MODEL,
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
    keywords = [
        "te lo consulto", "consulto con santiago", "te paso con santiago",
        "aviso en breve", "le aviso a santiago", "aviso a santiago",
        "comunico con santiago", "santiago para que", "santiago se comunique",
        "te paso el whatsapp de santiago", "te paso el número de santiago",
        "+54 9 2494 20-9464", "2494 20-9464", "le mando un resumen",
    ]
    return any(kw in text.lower() for kw in keywords)

def _wa_notify_santiago(lead: dict, summary: str, emoji: str = "🔥") -> None:
    """Manda un WhatsApp a Santiago con el resumen del lead."""
    name  = lead.get("name") or "Sin nombre"
    phone = lead.get("phone", "")
    msg = (
        f"{emoji} *{name}*\n"
        f"📱 wa.me/{phone}\n\n"
        f"{summary[:200]}"
    )
    try:
        wa_send_internal(msg)
        print(f"[WA Santiago] notificado sobre {name} ({phone})")
    except Exception as e:
        print(f"[WA Santiago] error: {e}")

def notify_urgency(lead: dict, last_user_message: str, urgency_summary: str) -> None:
    """Notifica a Santiago que hay un lead caliente listo para tomar."""
    name  = lead.get("name") or "Sin nombre"
    phone = lead.get("phone", "")
    summary = urgency_summary or last_user_message[:120]
    _wa_notify_santiago(lead, summary, emoji="🔥")

def notify_escalation(lead: dict, last_user_message: str) -> None:
    """Notifica con resumen del lead — incluye notas del form + estado extraído de la conversación."""
    name = lead.get("name") or "Sin nombre"
    phone = lead.get("phone", "")
    lead_id = lead.get("id", "")
    # Armar resumen: notas del formulario + estado extraído
    parts = []
    notas = (lead.get("notas") or "").strip()
    if notas:
        parts.append(f"Form: {notas[:300]}")
    try:
        history = messages_get(lead_id, limit=40) if lead_id else []
        if history:
            state = _extract_lead_state(history)
            if state:
                parts.append(f"Estado: {state[:300]}")
    except Exception as e:
        print(f"[notify_escalation] resumen error: {e}")
    parts.append(f"Último: {last_user_message[:120]}")
    summary = "\n".join(parts)
    _wa_notify_santiago(lead, summary, emoji="👋")

# ── Deduplicación Wati ────────────────────────────────────────────────────────

_seen_wati_msgs: dict = {}  # whatsappMessageId → timestamp
_DEDUP_TTL = 7200           # 2 horas

def _wati_is_duplicate(msg_id: str) -> bool:
    """True si el mensaje ya fue procesado. Limpia entradas viejas en cada llamada."""
    if not msg_id:
        return False
    now = time.time()
    stale = [k for k, t in _seen_wati_msgs.items() if now - t > _DEDUP_TTL]
    for k in stale:
        del _seen_wati_msgs[k]
    if msg_id in _seen_wati_msgs:
        return True
    _seen_wati_msgs[msg_id] = now
    return False

def _pause_on_operator(phone: str) -> None:
    """Pausa Sofía cuando un operador humano tomó la conversación."""
    try:
        lead = lead_get_or_create(phone)
        if not lead.get("sofia_paused"):
            lead_set_paused(lead["id"], True)
            print(f"[Wati] Operador activo → Sofía pausada para {phone}")
    except Exception as e:
        print(f"[Wati pause] {e}")

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
        # Santiago escribe desde su WhatsApp personal → modo manager (informe de leads)
        if SANTIAGO_PHONE and re.sub(r"[^\d]", "", from_phone)[-10:] == re.sub(r"[^\d]", "", SANTIAGO_PHONE)[-10:]:
            _handle_manager(user_text)
            return

        lead = lead_get_or_create(from_phone)
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
        is_new_lead = len(history) <= 1

        # Tasación: propietario que quiere vender — prioridad sobre urgencia normal
        is_tasacion = detect_tasacion(user_text)

        # El primer mensaje de un formulario Meta incluye los datos del form en el cuerpo
        # del WhatsApp — "plazo: 1 a 3 meses" etc. generaba falsos positivos de urgencia
        is_form_first_message = (
            "completé el formulario" in user_text.lower()
            and len(history) <= 1
        )

        # Si llegó un form pero las notas están vacías (Meta leadgen webhook se perdió
        # durante caída del bot), parsear los campos del mensaje y guardarlos como notas.
        # Esto le da a Sofía contexto (presupuesto, plazo, objetivo) aunque no sepa la
        # propiedad — y el prompt le indica que pregunte cuál propiedad era.
        if is_form_first_message and not lead_notas:
            parsed_fields = {}
            for line in user_text.split("\n"):
                line = line.strip()
                if ":" in line and not line.startswith("¡") and not line.lower().startswith("hola"):
                    key, _, val = line.partition(":")
                    key, val = key.strip(), val.strip()
                    if key and val:
                        parsed_fields[key] = val
            if parsed_fields:
                notas_lines = ["Datos del formulario (sin propiedad específica — proponer la mejor opción de la cartera según presupuesto + dormitorios + objetivo):"]
                notas_lines += [f"{k}: {v}" for k, v in parsed_fields.items()]
                lead_notas = "\n".join(notas_lines)
                try:
                    _sfre_client().table("chat_leads").update({"notas": lead_notas}).eq("id", lead_id).execute()
                    print(f"[WA] Notas recuperadas del form para lead {lead_id}")
                except Exception as _e:
                    print(f"[WA] Error guardando notas recuperadas: {_e}")

        lead_name = lead.get("name") or profile_name or ""

        if is_tasacion:
            reply = sofia_reply(history, user_text, lead_notas, tasacion=True)
            message_save(lead_id, "assistant", reply)
            wa_send(from_phone, reply, fallback_name=lead_name)
            notify_tasacion(lead, user_text)
            lead_set_paused(lead_id, True)
            attrs = _classify_lead_from_state("", lead_notas, reply, is_urgent=True, is_new=is_new_lead)
            attrs["tipo_lead"] = "tasacion"
            attrs["resumen"] = f"Quiere vender/tasar — {user_text[:120]}"
            threading.Thread(target=wati_update_contact_attrs, args=(from_phone, attrs), daemon=True).start()
        else:
            # No detectar urgencia en el primer mensaje de formulario (falsos positivos)
            is_urgent, urgency_summary = (False, "") if is_form_first_message else detect_urgency(user_text, history)

            reply = sofia_reply(history, user_text, lead_notas, escalate=is_urgent)
            message_save(lead_id, "assistant", reply)
            wa_send(from_phone, reply, fallback_name=lead_name)

            # Clasificación centralizada — usa el estado extraído + notas + reply
            history_for_state = history + [{"role": "user", "content": user_text}]
            lead_state_text = _extract_lead_state(history_for_state)
            attrs = _classify_lead_from_state(lead_state_text, lead_notas, reply, is_urgent=is_urgent, is_new=is_new_lead)

            # Construir resumen de una línea para Santiago
            summary_bits = []
            if attrs.get("dormitorios"): summary_bits.append(f"{attrs['dormitorios']} dorm")
            if attrs.get("presupuesto_usd"): summary_bits.append(f"USD {attrs['presupuesto_usd']}")
            if attrs.get("tipo_lead"): summary_bits.append(attrs["tipo_lead"])
            if attrs.get("propiedad_interes"): summary_bits.append(f"int: {attrs['propiedad_interes']}")
            if attrs.get("plazo"): summary_bits.append(f"plazo: {attrs['plazo']}")
            if attrs.get("forma_pago"): summary_bits.append(attrs["forma_pago"])
            if summary_bits:
                attrs["resumen"] = " · ".join(summary_bits)

            if is_urgent:
                print(f"[WA] Lead caliente detectado: {from_phone} — {urgency_summary}")
                notify_urgency(lead, user_text, urgency_summary)
                lead_set_paused(lead_id, True)
                attrs["resumen"] = urgency_summary[:200] or attrs.get("resumen", "")
            elif needs_escalation(reply):
                notify_escalation(lead, user_text)

            threading.Thread(target=wati_update_contact_attrs, args=(from_phone, attrs), daemon=True).start()
    except Exception as e:
        import traceback
        print(f"[WA Error] {e}")
        traceback.print_exc()
        try:
            wa_send(from_phone, "Disculpá, tuve un problema técnico. Te contactamos en breve.")
        except Exception:
            pass

# ── Envío de documentos PDF ────────────────────────────────────────────────────

def wa_send_doc(to: str, doc_url: str, filename: str) -> None:
    if WATI_API_URL and WATI_API_TOKEN:
        # Wati: enviar documento como link de texto (template de media no disponible en session msgs)
        phone = re.sub(r"[^\d]", "", to)
        resp = http_requests.post(
            f"{WATI_API_URL.rstrip('/')}/api/v1/sendSessionMessage/{phone}",
            params={"messageText": f"📄 {filename}\n{doc_url}"},
            headers={"Authorization": f"Bearer {WATI_API_TOKEN}"},
            timeout=10,
        )
        print(f"[Wati doc → {phone}] {resp.status_code}")
    elif WA_TOKEN and WA_PHONE_ID:
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
    if digits.startswith("0"):
        digits = "54" + digits[1:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "54" + digits
    elif not digits.startswith("54"):
        digits = "54" + digits
    # Móviles argentinos: 54 + 9 + área(3) + número(6) = 13 dígitos
    # Si tiene 12 dígitos y no tiene el 9 de móvil → insertarlo
    if len(digits) == 12 and digits.startswith("54") and digits[2] != "9":
        digits = "549" + digits[2:]
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

_PROPERTY_CODE_MAP = {
    "GARIBALDI431": "Garibaldi 431",
    "SANLO420": "San Lorenzo 420",
    "SANLORENZO420": "San Lorenzo 420",
    "ROCA36": "Roca 36",
    "CHACABUCO977": "Chacabuco 977",
    "GARIBALDI451": "Garibaldi 451",
    "CONSTITUCION862": "Constitución 862",
    "ALBERDI348": "Alberdi 348",
    "GUATEMALA1098": "Guatemala 1098",
    "SARMIENTO1200": "Sarmiento 1200",
    "PAZ341": "Paz 341",
}

def _resolve_property_name(raw: str) -> str:
    """Convierte códigos de campaña Meta Ads (V4_SOFI_GARIBALDI431, etc.) a nombres legibles.
    Si no matchea, devuelve el string original limpio."""
    if not raw:
        return raw
    s = raw.strip()
    # Strip prefijos típicos: V1_SOFI_, V2_, V4_SOFI_, SOFI_, etc.
    cleaned = re.sub(r'^V\d+[_-]?(?:SOFI[_-])?', '', s, flags=re.IGNORECASE)
    cleaned = re.sub(r'^SOFI[_-]', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.upper().replace('-', '').replace('_', '').replace(' ', '')
    if cleaned in _PROPERTY_CODE_MAP:
        return _PROPERTY_CODE_MAP[cleaned]
    # Intentar match parcial (por si el código tiene sufijos)
    for code, name in _PROPERTY_CODE_MAP.items():
        if code in cleaned:
            return name
    return raw  # devolver original si no matchea

def _parse_lead_fields(field_data: list) -> dict:
    """Extrae todos los campos del formulario de Meta."""
    NAME_KEYS  = {"full_name", "nombre_completo", "nombre", "name"}
    PHONE_KEYS = {"phone_number", "telefono", "phone", "celular", "whatsapp",
                  "número_de_teléfono", "numero_de_telefono", "teléfono"}
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
    propiedad = META_FORM_MAP.get(form_id) or _resolve_property_name(form_id) or "una de nuestras propiedades"
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
            if phone:
                try:
                    # No mandar bienvenida si ya hay conversación activa con este número
                    prev_msgs = sb.table("chat_messages").select("id").eq("lead_id", lead_id).limit(1).execute()
                    if prev_msgs.data:
                        print(f"[LeadAds] Lead {lead_id} ya tiene mensajes — omitiendo bienvenida")
                    else:
                        msg = sofia_reply([], "[primer contacto — enviá tu mensaje de bienvenida]", lead_notas=notas)
                        wa_send(phone, msg, fallback_name=nombre or "")
                        message_save(lead_id, "assistant", msg)
                        print(f"[LeadAds] Bienvenida enviada a {phone}")
                except Exception as wa_err:
                    print(f"[LeadAds] Error enviando bienvenida a {phone}: {wa_err}")

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
        import hmac as _hmac, hashlib
        raw_body = request.get_data()
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + _hmac.new(
            META_APP_SECRET.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        print(f"[LeadAds] sig_received={sig_header[:30]}... expected={expected[:30]}... body_len={len(raw_body)}")
        if not _hmac.compare_digest(sig_header, expected):
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


# ── Webhook Wati BSP ──────────────────────────────────────────────────────────

@app.route("/wati/webhook", methods=["POST"])
def wati_receive():
    """Recibe mensajes entrantes de WhatsApp vía Wati BSP."""
    # Validación de token secreto — rechazar requests no autorizados
    if WATI_WEBHOOK_SECRET:
        token = request.args.get("token") or request.headers.get("X-Wati-Token", "")
        if token != WATI_WEBHOOK_SECRET:
            print(f"[Wati webhook] Token inválido — rechazado")
            return "unauthorized", 401

    data = request.get_json(silent=True) or {}
    try:
        event_type = data.get("eventType", "")

        # Filtrar PRIMERO los eventos de tracking (delivered/read/sent) — vienen con
        # owner: true porque corresponden a mensajes salientes (incluso los de Sofía
        # misma). NO son takeover real.
        if event_type and event_type not in ("message", "messageReceived"):
            waid = data.get("waId", "?")
            print(f"[Wati event] {event_type} — {waid}")
            return "ok", 200

        # Operador humano REAL envió un mensaje manual desde Wati → pausar Sofía.
        # Solo cuenta como takeover si:
        #  1. owner == True (mensaje saliente)
        #  2. hay operatorEmail/operatorName (humano logueado en Wati lo mandó)
        #  3. el eventType pasó el filtro de arriba (no es status update)
        if data.get("owner") and (data.get("operatorEmail") or data.get("operatorName")):
            op_phone = data.get("waId", "")
            if op_phone:
                threading.Thread(target=_pause_on_operator, args=(op_phone,), daemon=True).start()
            return "ok", 200

        # Deduplicación — Wati reintenta hasta 144 veces si no responde en 5s
        msg_id = data.get("whatsappMessageId") or data.get("id", "")
        if _wati_is_duplicate(msg_id):
            print(f"[Wati dedup] {msg_id} ya procesado")
            return "ok", 200

        # Filtro de antigüedad — descartar mensajes de más de 10 minutos
        # Esto evita que retries acumulados durante downtime se procesen al reiniciar
        msg_ts = data.get("timestamp")
        if msg_ts:
            try:
                msg_age_secs = time.time() - float(msg_ts)
                if msg_age_secs > 600:
                    print(f"[Wati] Mensaje de hace {int(msg_age_secs//60)}min descartado (retry tras downtime) — {data.get('waId','?')}")
                    return "ok", 200
            except Exception:
                pass

        # NOTA: el check de operator takeover real ya pasó arriba (data.get("owner") == True).
        # Wati incluye operatorEmail/operatorName en TODOS los mensajes de conversaciones
        # asignadas, incluso entrantes del lead — chequear acá causaba falsos positivos
        # que pausaban Sofía para casi todos los leads. Si llegaste hasta acá el mensaje
        # es del lead, no del operador, así que seguimos procesando normalmente.

        msg_type   = (data.get("type") or "").lower()
        from_phone = data.get("waId", "")
        contact    = data.get("messageContact") or {}
        if isinstance(contact, str):
            contact = {}
        wa_profile = contact.get("fullName") or contact.get("firstName") or ""

        if not from_phone:
            return "ok", 200

        if msg_type == "text":
            user_text = data.get("text") or ""
            if not user_text:
                return "ok", 200
        elif msg_type == "audio":
            raw_data = data.get("data") or {}
            print(f"[Wati audio raw] type={type(raw_data).__name__} value={str(raw_data)[:200]}")
            if isinstance(raw_data, str):
                media_url = raw_data
            else:
                media_url = raw_data.get("url", "")
            if OPENAI_KEY and media_url:
                try:
                    wati_headers = {"Authorization": f"Bearer {WATI_API_TOKEN}"} if WATI_API_TOKEN else {}
                    audio_resp = http_requests.get(media_url, headers=wati_headers, timeout=15)
                    user_text  = transcribe_audio(audio_resp.content) if audio_resp.ok else ""
                    if not user_text:
                        print(f"[Wati audio] descarga falló: {audio_resp.status_code}")
                except Exception as e:
                    print(f"[Wati audio] error: {e}")
                    user_text = ""
            else:
                user_text = ""
            if not user_text:
                wa_send(from_phone, "No escuché bien el audio 😅 ¿Me lo podés escribir?")
                return "ok", 200
            print(f"[Wati audio transcripto] {user_text[:80]}")
        elif msg_type in ("button", "interactive"):
            # Respuesta a botón de template: extraer el texto del botón presionado
            button_text = (data.get("text") or
                           (data.get("button") or {}).get("text") or
                           (data.get("interactive") or {}).get("button_reply", {}).get("title") or "")
            if not button_text:
                print(f"[Wati botón] sin texto — payload: {str(data)[:200]}")
                return "ok", 200
            user_text = button_text
            print(f"[Wati botón] {from_phone}: {user_text}")
        else:
            print(f"[Wati tipo ignorado] {msg_type} de {from_phone}")
            return "ok", 200

        print(f"[Wati] {from_phone}: {user_text[:80]}")

        with _pending_lock:
            if from_phone in _pending:
                _pending[from_phone]['timer'].cancel()
                _pending[from_phone]['texts'].append(user_text)
                if wa_profile and not _pending[from_phone].get('profile_name'):
                    _pending[from_phone]['profile_name'] = wa_profile
            else:
                _pending[from_phone] = {'texts': [user_text], 'profile_name': wa_profile}
            t = threading.Timer(DEBOUNCE_SECS, _fire, args=[from_phone])
            _pending[from_phone]['timer'] = t
            t.start()

    except Exception as e:
        import traceback
        print(f"[Wati Error] {e}")
        traceback.print_exc()

    return "ok", 200


# ── Webhook Respond.io BSP ────────────────────────────────────────────────────

@app.route("/respond/webhook", methods=["POST"])
def respond_receive():
    """Recibe mensajes entrantes de WhatsApp vía Respond.io BSP."""
    data = request.get_json(silent=True) or {}
    try:
        contact = data.get("contact", {})
        from_phone = re.sub(r"[^\d]", "", contact.get("phone", ""))
        if not from_phone:
            return "ok", 200

        first = contact.get("firstName") or ""
        last  = contact.get("lastName") or ""
        wa_profile = (first + " " + last).strip()

        for event in data.get("events", []):
            if event.get("type") != "message":
                continue
            msg = event.get("message", {})
            # Ignorar mensajes salientes (propios de Sofía)
            if (msg.get("direction") or "").upper() == "OUTBOUND":
                continue

            msg_type = (msg.get("type") or "").upper()

            if msg_type == "TEXT":
                user_text = msg.get("text", "")
                if not user_text:
                    continue
            elif msg_type in ("AUDIO", "VOICE"):
                wa_send(from_phone, "No escuché bien el audio 😅 ¿Me lo podés escribir?")
                continue
            else:
                print(f"[Respond.io tipo ignorado] {msg_type} de {from_phone}")
                continue

            print(f"[Respond.io] {from_phone}: {user_text[:80]}")

            with _pending_lock:
                if from_phone in _pending:
                    _pending[from_phone]['timer'].cancel()
                    _pending[from_phone]['texts'].append(user_text)
                    if wa_profile and not _pending[from_phone].get('profile_name'):
                        _pending[from_phone]['profile_name'] = wa_profile
                else:
                    _pending[from_phone] = {'texts': [user_text], 'profile_name': wa_profile}
                t = threading.Timer(DEBOUNCE_SECS, _fire, args=[from_phone])
                _pending[from_phone]['timer'] = t
                t.start()

    except Exception as e:
        print(f"[Respond.io Error] {e}")

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

@app.route("/test/run", methods=["POST"])
def test_run():
    secret = request.args.get("secret", "")
    if secret != os.environ.get("UPTIMEROBOT_SECRET", "sfre-monitor-2026"):
        return jsonify({"error": "unauthorized"}), 403
    threading.Thread(target=sofia_auto_test, daemon=True).start()
    return jsonify({"ok": True, "msg": "Test iniciado — resultados por WhatsApp en ~2 min"})

@app.route("/uptimerobot", methods=["GET", "POST"])
def uptimerobot_webhook():
    secret = request.args.get("secret") or (request.json or {}).get("secret", "")
    expected = os.environ.get("UPTIMEROBOT_SECRET", "sfre-monitor-2026")
    if secret != expected:
        return jsonify({"error": "unauthorized"}), 403
    alert_type = request.args.get("alertType") or (request.json or {}).get("alertType", "")
    if alert_type == "2":  # 2 = back up
        wa_send_internal("✅ *Sofía volvió* — el servidor está online de nuevo.")
    return jsonify({"ok": True})

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

    lines = [f"📊 *Resumen Sofía — últimas {hours}hs*"]
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


@app.route("/admin/digest", methods=["POST"])
def trigger_digest():
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    hours = int(request.get_json(silent=True).get("hours", 2))
    threading.Thread(target=send_digest, args=[hours], daemon=True).start()
    return jsonify({"ok": True, "hours": hours})

@app.route("/admin/test-sofia", methods=["POST"])
def trigger_sofia_test():
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    threading.Thread(target=sofia_auto_test, daemon=True).start()
    return jsonify({"ok": True, "msg": "Prueba iniciada — resultado por WhatsApp en ~30s"})


# ── Notificaciones internas → Santiago ────────────────────────────────────────

SANTIAGO_WA = SANTIAGO_PHONE or "5492494557754"

@app.route("/notify/santiago", methods=["POST"])
def notify_santiago():
    """Endpoint para agentes de Paperclip — manda un mensaje a Santiago por WhatsApp."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()
    if not text:
        return jsonify({"error": "text requerido"}), 400
    try:
        wa_send_internal(text)
        print(f"[notify/santiago] Mensaje enviado: {text[:60]}...")
        return jsonify({"ok": True})
    except RuntimeError as e:
        print(f"[notify/santiago] FALLO: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/wati/templates", methods=["GET"])
def wati_templates():
    """Lista los templates aprobados en WATI."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if not WATI_API_URL or not WATI_API_TOKEN:
        return jsonify({"ok": False, "error": "WATI_API_URL o WATI_API_TOKEN no configurados"})
    resp = http_requests.get(
        f"{WATI_API_URL.rstrip('/')}/api/v1/getMessageTemplates?pageSize=50",
        headers={"Authorization": f"Bearer {WATI_API_TOKEN}"},
        timeout=10,
    )
    templates = resp.json().get("messageTemplates", [])
    return jsonify({
        "status": resp.status_code,
        "templates": [
            {"name": t.get("elementName"), "status": t.get("status"), "body": t.get("body", "")[:100]}
            for t in templates
        ]
    })

@app.route("/wati/proxy", methods=["GET", "POST", "PUT", "PATCH"])
def wati_proxy():
    """Proxy genérico hacia la API de Wati. Pasar _path en query string para el endpoint."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if not WATI_API_URL or not WATI_API_TOKEN:
        return jsonify({"ok": False, "error": "WATI_API_URL o WATI_API_TOKEN no configurados"})
    wati_path = request.args.get("_path", "")
    if not wati_path:
        return jsonify({"error": "_path requerido"}), 400
    body = request.get_json(silent=True) or {}
    method = request.method
    url = f"{WATI_API_URL.rstrip('/')}/{wati_path.lstrip('/')}"
    params = {k: v for k, v in request.args.items() if k != "_path"}
    fn = http_requests.post if method == "POST" else http_requests.get
    resp = fn(url, json=body if method != "GET" else None, params=params,
              headers={"Authorization": f"Bearer {WATI_API_TOKEN}", "Content-Type": "application/json"},
              timeout=15)
    try:
        return jsonify({"status": resp.status_code, "body": resp.json()})
    except Exception:
        return jsonify({"status": resp.status_code, "body": resp.text[:1000]})

@app.route("/admin/reclassify-all", methods=["POST"])
def admin_reclassify_all():
    """Reclasifica todos los leads en Supabase aplicando la lógica nueva y los manda a Wati."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    days = int(request.args.get("days", "30"))
    try:
        from datetime import datetime, timedelta, timezone
        sb = _sfre_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        leads = sb.table("chat_leads").select("*").gte("last_message_at", cutoff).execute()
        results = []
        for lead in (leads.data or []):
            phone = lead.get("phone")
            if not phone: continue
            lead_id = lead["id"]
            try:
                msgs_res = sb.table("chat_messages").select("role,content").eq("lead_id", lead_id).order("created_at").execute()
                msgs = msgs_res.data or []
            except Exception:
                msgs = []
            lead_notas = lead.get("notas") or ""
            last_reply = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "")
            lead_state = _extract_lead_state(msgs)
            is_new = len(msgs) <= 2
            # Detectar caliente por keywords del último user message
            last_user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")
            is_urgent = any(kw in last_user.lower() for kw in ["cuándo puedo ir", "cuando puedo ir", "reservar", "seña", "señar", "quiero avanzar", "coordiná", "coordinar visita"])
            attrs = _classify_lead_from_state(lead_state, lead_notas, last_reply, is_urgent=is_urgent, is_new=is_new)
            # Resumen
            summary_bits = []
            if attrs.get("dormitorios"): summary_bits.append(f"{attrs['dormitorios']} dorm")
            if attrs.get("presupuesto_usd"): summary_bits.append(f"USD {attrs['presupuesto_usd']}")
            if attrs.get("tipo_lead"): summary_bits.append(attrs["tipo_lead"])
            if attrs.get("propiedad_interes"): summary_bits.append(f"int: {attrs['propiedad_interes']}")
            if attrs.get("plazo"): summary_bits.append(f"plazo: {attrs['plazo']}")
            if summary_bits: attrs["resumen"] = " · ".join(summary_bits)
            try:
                wati_update_contact_attrs(phone, attrs)
                results.append({"phone": phone, "name": lead.get("name"), "attrs": attrs})
            except Exception as e:
                results.append({"phone": phone, "error": str(e)})
        return jsonify({"ok": True, "count": len(results), "samples": results[:5]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/admin/cleanup-form-notas", methods=["POST"])
def admin_cleanup_form_notas():
    """Aplica _resolve_property_name a las notas existentes que tengan códigos V4_SOFI_*."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        sb = _sfre_client()
        # Traer todos los leads cuyas notas contengan códigos V*_SOFI_ o SOFI_
        leads = sb.table("chat_leads").select("id,phone,notas").execute()
        updated = []
        for lead in (leads.data or []):
            notas = lead.get("notas") or ""
            if not notas:
                continue
            # Buscar códigos V*_SOFI_PROPIEDAD en las notas
            new_notas = re.sub(
                r'V\d+[_-]?SOFI[_-][A-Z0-9]+',
                lambda m: _resolve_property_name(m.group(0)),
                notas,
                flags=re.IGNORECASE
            )
            if new_notas != notas:
                sb.table("chat_leads").update({"notas": new_notas}).eq("id", lead["id"]).execute()
                updated.append({"phone": lead["phone"], "old": notas[:80], "new": new_notas[:80]})
        return jsonify({"ok": True, "updated_count": len(updated), "samples": updated[:10]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/admin/recent-conversations", methods=["GET"])
def admin_recent_conversations():
    """Devuelve los últimos N leads (con cualquier mensaje en los últimos N días) y sus conversaciones completas."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    days = int(request.args.get("days", "7"))
    limit = int(request.args.get("limit", "50"))
    try:
        from datetime import datetime, timedelta, timezone
        sb = _sfre_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        leads = sb.table("chat_leads").select("*").gte("last_message_at", cutoff).order("last_message_at", desc=True).limit(limit).execute()
        out = []
        for lead in (leads.data or []):
            msgs = sb.table("chat_messages").select("role,content,created_at").eq("lead_id", lead["id"]).order("created_at").execute()
            out.append({"lead": lead, "messages": msgs.data or []})
        return jsonify({"ok": True, "count": len(out), "conversations": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/admin/lead-debug", methods=["GET"])
def admin_lead_debug():
    """Devuelve el estado de un lead + últimos mensajes."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    phone = request.args.get("phone", "").strip()
    if not phone:
        return jsonify({"error": "phone requerido"}), 400
    try:
        sb = _sfre_client()
        lead_res = sb.table("chat_leads").select("*").eq("phone", phone).execute()
        if not lead_res.data:
            return jsonify({"ok": False, "error": "lead no encontrado", "phone": phone})
        lead = lead_res.data[0]
        msgs = sb.table("chat_messages").select("role,content,created_at").eq("lead_id", lead["id"]).order("created_at").execute()
        return jsonify({"ok": True, "lead": lead, "messages": msgs.data or []})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/admin/lead-unpause", methods=["POST"])
def admin_lead_unpause():
    """Pone sofia_paused=false para un lead. Si phone='ALL', despausa todos."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    phone = (request.get_json(silent=True) or {}).get("phone", "").strip()
    if not phone:
        return jsonify({"error": "phone requerido"}), 400
    try:
        sb = _sfre_client()
        if phone == "ALL":
            res = sb.table("chat_leads").update({"sofia_paused": False}).eq("sofia_paused", True).execute()
        else:
            res = sb.table("chat_leads").update({"sofia_paused": False}).eq("phone", phone).execute()
        return jsonify({"ok": True, "updated": len(res.data or [])})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/evo/debug", methods=["GET"])
def evo_debug():
    """Verifica que la instancia de Evolution API está conectada."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if not EVOLUTION_URL or not EVOLUTION_KEY:
        return jsonify({"ok": False, "error": "EVOLUTION_API_URL o EVOLUTION_API_KEY no configurados"})
    resp = http_requests.get(
        f"{EVOLUTION_URL.rstrip('/')}/instance/fetchInstances",
        headers={"apikey": EVOLUTION_KEY},
        timeout=10,
    )
    return jsonify({"status": resp.status_code, "evolution_response": resp.json()})

@app.route("/wa/debug", methods=["GET"])
def wa_debug():
    """Diagnostica el token de WhatsApp contra la API de Meta."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if not WA_TOKEN or not WA_PHONE_ID:
        return jsonify({"ok": False, "error": "WHATSAPP_TOKEN o WHATSAPP_PHONE_ID no configurados en Railway"})
    resp = http_requests.get(
        f"https://graph.facebook.com/v20.0/{WA_PHONE_ID}",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        timeout=10,
    )
    return jsonify({"status": resp.status_code, "meta_response": resp.json()})


@app.route("/wa/fix-subscription", methods=["POST"])
def wa_fix_subscription():
    """Suscribe el número de WhatsApp al app — fix para mensajes no recibidos."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if not WA_TOKEN or not WA_PHONE_ID:
        return jsonify({"ok": False, "error": "WHATSAPP_TOKEN o WHATSAPP_PHONE_ID no configurados"})

    # 1. Obtener WABA ID desde el phone ID
    phone_resp = http_requests.get(
        f"https://graph.facebook.com/v20.0/{WA_PHONE_ID}",
        params={"fields": "id,display_phone_number,whatsapp_business_account_id"},
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        timeout=10,
    )
    phone_data = phone_resp.json()
    if "error" in phone_data:
        return jsonify({"ok": False, "step": "get_phone", "error": phone_data["error"]})

    waba_id = phone_data.get("whatsapp_business_account_id")
    if not waba_id:
        return jsonify({"ok": False, "step": "get_waba_id", "phone_data": phone_data,
                        "error": "whatsapp_business_account_id no encontrado en la respuesta"})

    # 2. Suscribir el WABA al app
    sub_resp = http_requests.post(
        f"https://graph.facebook.com/v20.0/{waba_id}/subscribed_apps",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        timeout=10,
    )
    sub_data = sub_resp.json()

    # 3. Verificar suscripciones actuales
    check_resp = http_requests.get(
        f"https://graph.facebook.com/v20.0/{waba_id}/subscribed_apps",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        timeout=10,
    )

    return jsonify({
        "ok": sub_data.get("success", False),
        "waba_id": waba_id,
        "phone_number": phone_data.get("display_phone_number"),
        "subscribe_result": sub_data,
        "current_subscriptions": check_resp.json(),
    })


def meta_leads_reconcile() -> None:
    """Compara leads de Meta (últimas 8hs) con Supabase e importa los que faltan."""
    if not META_PAGE_TOKEN:
        return
    try:
        from datetime import datetime, timedelta, timezone as tz
        import re as _re

        PAGE_ID = "100744281781455"
        since   = int((datetime.now(tz.utc) - timedelta(hours=8)).timestamp())
        sb      = _sfre_client()

        db_phones = set(
            l["phone"]
            for l in sb.table("chat_leads").select("phone").execute().data or []
        )

        forms_r = http_requests.get(
            f"https://graph.facebook.com/v20.0/{PAGE_ID}/leadgen_forms",
            params={"access_token": META_PAGE_TOKEN, "limit": 30, "fields": "id,name"},
            timeout=15,
        ).json()

        if "error" in forms_r:
            print(f"[Reconcile] Token error: {forms_r['error']['message'][:80]}")
            tg_send("⚠️ *META\\_PAGE\\_TOKEN vencido* — regenerar en Graph Explorer y actualizar Railway")
            return

        nuevos = []
        for form in forms_r.get("data", []):
            leads_r = http_requests.get(
                f"https://graph.facebook.com/v20.0/{form['id']}/leads",
                params={
                    "access_token": META_PAGE_TOKEN,
                    "limit": 50,
                    "fields": "id,field_data,created_time",
                    "filtering": f'[{{"field":"time_created","operator":"GREATER_THAN","value":{since}}}]',
                },
                timeout=15,
            ).json()

            for lead in leads_r.get("data", []):
                fields    = _parse_lead_fields(lead.get("field_data", []))
                phone_raw = fields["phone"]
                if not phone_raw:
                    continue
                phone = _normalize_phone(phone_raw)
                if phone in db_phones:
                    continue
                nombre    = fields["name"]
                prop_name = META_FORM_MAP.get(form["id"]) or _resolve_property_name(form.get("name", ""))
                notas     = _build_form_notas(prop_name, nombre, fields["extras"])
                # Insertar lead
                res     = sb.table("chat_leads").insert(
                    {"phone": phone, "name": nombre or None, "notas": notas, "status": "nuevo"}
                ).execute()
                lead_id = res.data[0]["id"]
                db_phones.add(phone)
                nuevos.append({"lead_id": lead_id, "phone": phone, "name": nombre, "prop": prop_name})
                print(f"[Reconcile] Importado: {nombre} ({phone}) — {prop_name}")

        if nuevos:
            for n in nuevos:
                try:
                    prev = _sfre_client().table("chat_messages").select("id").eq("lead_id", n["lead_id"]).limit(1).execute()
                    if prev.data:
                        print(f"[Reconcile] {n['phone']} ya tiene mensajes — omitiendo bienvenida")
                        continue
                    msg = sofia_reply([], "[primer contacto — enviá tu mensaje de bienvenida]", lead_notas=n.get("notas", f"Origen: Meta Ads — {n['prop']}\nNombre declarado en formulario: {n['name']}"))
                    wa_send(n["phone"], msg)
                    message_save(n["lead_id"], "assistant", msg)
                except Exception as e:
                    print(f"[Reconcile] Error enviando a {n['phone']}: {e}")
                time.sleep(2)
            tg_send(f"🔄 *Reconciliación automática*: {len(nuevos)} lead(s) recuperado(s) de Meta y contactado(s) por Sofía.")
        else:
            print("[Reconcile] Sin leads nuevos faltantes.")
    except Exception as e:
        print(f"[Reconcile] Error: {e}")


def meta_leads_reconcile_historical(days: int = 90, contact_new: bool = True) -> dict:
    """Importa todos los leads de Meta de los últimos N días y opcionalmente los contacta."""
    if not META_PAGE_TOKEN:
        return {"error": "META_PAGE_TOKEN no configurado"}
    from datetime import datetime, timedelta, timezone as tz

    PAGE_ID = "100744281781455"
    since   = int((datetime.now(tz.utc) - timedelta(days=days)).timestamp())
    sb      = _sfre_client()

    db_phones = set(
        l["phone"]
        for l in sb.table("chat_leads").select("phone").execute().data or []
    )

    forms_r = http_requests.get(
        f"https://graph.facebook.com/v20.0/{PAGE_ID}/leadgen_forms",
        params={"access_token": META_PAGE_TOKEN, "limit": 30, "fields": "id,name"},
        timeout=15,
    ).json()
    if "error" in forms_r:
        return {"error": forms_r["error"]["message"]}

    importados = []
    omitidos   = 0

    for form in forms_r.get("data", []):
        # Paginar hasta 90 días — Meta devuelve hasta 100 por página
        after  = None
        while True:
            params = {
                "access_token": META_PAGE_TOKEN,
                "limit": 100,
                "fields": "id,field_data,created_time",
                "filtering": f'[{{"field":"time_created","operator":"GREATER_THAN","value":{since}}}]',
            }
            if after:
                params["after"] = after

            leads_r = http_requests.get(
                f"https://graph.facebook.com/v20.0/{form['id']}/leads",
                params=params,
                timeout=20,
            ).json()

            for lead in leads_r.get("data", []):
                fields    = _parse_lead_fields(lead.get("field_data", []))
                phone_raw = fields["phone"]
                if not phone_raw:
                    omitidos += 1
                    continue
                phone = _normalize_phone(phone_raw)
                if phone in db_phones:
                    omitidos += 1
                    continue
                nombre    = fields["name"]
                prop_name = META_FORM_MAP.get(form["id"]) or _resolve_property_name(form.get("name", ""))
                notas     = _build_form_notas(prop_name, nombre, fields["extras"])
                try:
                    res     = sb.table("chat_leads").insert(
                        {"phone": phone, "name": nombre or None, "notas": notas, "status": "nuevo"}
                    ).execute()
                    lead_id = res.data[0]["id"]
                    db_phones.add(phone)
                    importados.append({"lead_id": lead_id, "phone": phone, "name": nombre, "prop": prop_name})
                    print(f"[Reconcile-hist] Importado: {nombre} ({phone}) — {prop_name}")
                except Exception as e:
                    print(f"[Reconcile-hist] Error insertando {phone}: {e}")

            # Paginación cursor
            cursor = leads_r.get("paging", {}).get("cursors", {})
            after  = cursor.get("after") if leads_r.get("paging", {}).get("next") else None
            if not after:
                break

    # Contactar solo los importados ahora (no los ya existentes)
    contactados = 0
    if contact_new and importados:
        for n in importados:
            try:
                msg = sofia_reply([], "", lead_notas=n.get("notas", f"Origen: Meta Ads — {n['prop']}\nNombre declarado en formulario: {n['name']}"))
                wa_send(n["phone"], msg)
                message_save(n["lead_id"], "assistant", msg)
                contactados += 1
            except Exception as e:
                print(f"[Reconcile-hist] Error enviando a {n['phone']}: {e}")
            time.sleep(3)

    summary = f"[Reconcile-hist] {len(importados)} importados, {contactados} contactados, {omitidos} omitidos (ya en DB o sin tel)"
    print(summary)
    tg_send(f"📋 *Reconciliación histórica ({days}d)*: {len(importados)} leads recuperados, {contactados} contactados por Sofía.")
    return {"importados": len(importados), "contactados": contactados, "omitidos": omitidos, "leads": importados}


@app.route("/admin/broadcast", methods=["GET", "POST"])
def admin_broadcast():
    """GET: lista templates Wati. POST: envía broadcast por template."""
    secret = request.args.get("secret", "")
    if secret != os.environ.get("UPTIMEROBOT_SECRET", "sfre-monitor-2026"):
        return jsonify({"error": "unauthorized"}), 403

    if request.method == "GET":
        # Listar templates + balance
        if not WATI_API_URL or not WATI_API_TOKEN:
            return jsonify({"error": "Wati no configurado"}), 500
        headers = {"Authorization": f"Bearer {WATI_API_TOKEN}"}
        templates_resp = http_requests.get(
            f"{WATI_API_URL.rstrip('/')}/api/v1/getMessageTemplates?pageSize=100",
            headers=headers, timeout=10,
        )
        templates = templates_resp.json().get("messageTemplates", [])
        # Intentar obtener balance/wallet
        wallet = {}
        for path in ["/api/v1/getWalletBalance", "/api/v1/wallet", "/api/v1/account/wallet"]:
            try:
                wr = http_requests.get(f"{WATI_API_URL.rstrip('/')}{path}", headers=headers, timeout=5)
                if wr.ok:
                    wallet = wr.json()
                    wallet["_endpoint"] = path
                    break
            except Exception:
                pass
        return jsonify({
            "wallet": wallet,
            "templates": [
                {"name": t.get("elementName"), "status": t.get("status"), "body": t.get("body"), "params": t.get("customParams", [])}
                for t in templates
            ]
        })

    # POST: enviar broadcast
    body = request.get_json(silent=True) or {}
    leads = body.get("leads", [])          # [{phone, nombre, propiedad?, params?}]
    template_name = body.get("template")   # nombre del template
    delay_s = int(body.get("delay_s", 3))  # pausa entre envíos

    if not leads or not template_name:
        return jsonify({"error": "leads y template requeridos"}), 400
    if not WATI_API_URL or not WATI_API_TOKEN:
        return jsonify({"error": "Wati no configurado"}), 500

    bcast_id = f"{template_name}_{int(time.time())}"

    receivers = []
    for lead in leads:
        phone = _normalize_phone(str(lead.get("phone", "")))
        receivers.append({
            "whatsappNumber": phone,
            "customParams": lead.get("params", []),
        })

    payload = {
        "template_name": template_name,
        "broadcast_name": bcast_id,
        "receivers": receivers,
    }

    resp = http_requests.post(
        f"{WATI_API_URL.rstrip('/')}/api/v1/sendTemplateMessages",
        json=payload,
        headers={"Authorization": f"Bearer {WATI_API_TOKEN}", "Content-Type": "application/json"},
        timeout=30,
    )
    print(f"[Broadcast] {resp.status_code} {resp.text[:400]}")

    if not resp.ok:
        return jsonify({"ok": False, "status": resp.status_code, "error": resp.text[:300]}), 502

    return jsonify({"ok": True, "leads": len(leads), "template": template_name, "broadcast_name": bcast_id, "wati_response": resp.json()})


@app.route("/meta/reconcile-historical", methods=["POST"])
def meta_reconcile_historical_endpoint():
    """Importa y contacta leads históricos de Meta que no están en la DB."""
    if API_KEY and request.headers.get("x-api-key", "") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    body         = request.get_json(silent=True) or {}
    days         = int(body.get("days", 90))
    contact_new  = bool(body.get("contact_new", True))
    # Correr en background para no hacer timeout en Railway
    threading.Thread(
        target=meta_leads_reconcile_historical,
        args=[days, contact_new],
        daemon=True,
    ).start()
    return jsonify({"status": "started", "days": days, "contact_new": contact_new})


_TEST_SCENARIOS = [
    {
        "tag": "inquilino-alquiler",
        "notas": "",
        "mensajes": [
            "Hola, busco un departamento para alquilar en Tandil",
            "Que tenga 1 dormitorio, zona centro",
            "¿Cuánto sale más o menos por mes?",
        ],
    },
    {
        "tag": "inversor-no-repetir-preguntas",
        "notas": "Formulario: Garibaldi 431.",
        "mensajes": [
            "Hola, vi el anuncio de Garibaldi",
            "Es para invertir, quiero poner en alquiler",
            "¿Cuánto rinde por mes?",
            "¿Y cuánto sale la unidad?",
        ],
    },
    {
        "tag": "en-pozo",
        "notas": "",
        "mensajes": [
            "Hola, busco algo en pozo para comprar",
            "¿Tienen algo en construcción?",
            "¿Cuánto hay que poner de entrada?",
        ],
    },
    {
        "tag": "recontacto-boton-interesado",
        "notas": "Recontacto previo enviado sobre Roca 36.",
        "mensajes": [
            "Sí me interesa",
            "¿Cuánto sale?",
            "¿Y cómo son los pagos?",
        ],
    },
    {
        "tag": "santiago-menciones",
        "notas": "Formulario: Chacabuco 977.",
        "mensajes": [
            "Hola, consulto por Chacabuco",
            "¿Cuánto sale el de 2 dormitorios?",
            "¿Tiene cochera incluida?",
            "¿Cuándo lo podría ver?",
        ],
    },
]

_RUBRICA_EVALUACION = """Evaluá esta conversación entre Sofía (secretaria de Santiago Funes, Tandil) y un lead de WhatsApp.

REGLAS QUE SOFÍA DEBE CUMPLIR:
1. En los primeros 2 mensajes NO propone visita ni llamada ("¿cuándo venís?", "coordinamos", "agendemos").
2. Hace UNA sola pregunta por mensaje. Nunca dos o más en el mismo mensaje.
3. NUNCA usa markdown: sin **, sin ##, sin guiones como viñetas, sin listas numeradas.
4. NUNCA usa tuteo. Voseo = verbos en segunda persona: "querés", "podés", "tenés", "pensás". NUNCA "quieres", "puedes", "tienes", "piensas". Nota: los posesivos "tu/tus" son iguales en tuteo y voseo — "¿Cuál es tu presupuesto?" es correcto en voseo. No lo marqués como error.
5. NUNCA dice: "¿Nos charlamos?", "¿Hablamos?", "agendamos una llamada", "jaja", "Buenísimo", "Bárbaro", "Genial".
6. Cuando nombra una propiedad específica, incluye el link en ese mismo mensaje.
7. El primer mensaje incluye presentación ("soy Sofía, la secretaria de Santiago") y UNA sola pregunta.
8. Si el lead dijo que quiere ALQUILAR como inquilino ("busco para alquilar", "quiero alquilar"), Sofía NO le ofrece comprar ni menciona inversión ni rentabilidad.
9. No repite preguntas que el lead ya respondió. Si ya dijo "para invertir", no le vuelve a preguntar si es para vivir o invertir.
10. Nombra a "Santiago" máximo UNA vez por conversación hasta que haya señal real de interés (querer ver, reservar, avanzar). No lo menciona en mensajes informativos. EXCEPCIÓN: la frase obligatoria de presentación "soy Sofía, la secretaria de Santiago" en el primer mensaje NO cuenta como mención — es obligatoria y no se penaliza.
11. Si el lead pregunta por algo "en pozo" o "en construcción", muestra solo Roca 36. No menciona Chacabuco 977 ni Garibaldi 431 como si fueran "en pozo".

Analizá mensaje por mensaje de Sofía. Sé específico con las frases exactas. Formato:

MSG 1: OK | FALLA: [regla N — transcribí la frase exacta que viola la regla]
MSG 2: OK | FALLA: [...]
...
VEREDICTO: SIN ERRORES | ERRORES ENCONTRADOS: [lista de los problemas, una línea cada uno]
"""


def sofia_auto_test() -> None:
    """Corre una conversación de prueba con Sofía y reporta errores por Telegram."""
    cl = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    all_errors: list[str] = []

    for scenario in _TEST_SCENARIOS:
        history: list[dict] = []
        notas = scenario["notas"]
        log_lines: list[str] = []

        for msg in scenario["mensajes"]:
            reply = sofia_reply(history, msg, notas)
            history.append({"role": "user", "content": msg})
            history.append({"role": "assistant", "content": reply})
            log_lines.append(f"Lead: {msg}")
            log_lines.append(f"Sofía: {reply}")

        conversation = "\n\n".join(log_lines)

        eval_r = cl.messages.create(
            model=SOFIA_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": f"{_RUBRICA_EVALUACION}\n\nCONVERSACIÓN:\n{conversation}"}],
        )
        evaluation = eval_r.content[0].text.strip()

        has_errors = "FALLA" in evaluation or "ERRORES ENCONTRADOS" in evaluation
        emoji = "⚠️" if has_errors else "✅"
        if has_errors:
            all_errors.append(scenario["tag"])

        print(f"[AutoTest] {emoji} escenario={scenario['tag']} errores={'sí' if has_errors else 'no'}")
        print(f"[AutoTest] CONVERSACIÓN:\n{conversation}")
        print(f"[AutoTest] EVALUACIÓN:\n{evaluation}")

    resumen_lines = []
    resumen_lines.append(f"{'⚠️' if all_errors else '✅'} AutoTest Sofía — {len(_TEST_SCENARIOS)} escenarios")
    if all_errors:
        resumen_lines.append(f"Fallaron: {', '.join(all_errors)}")
    else:
        resumen_lines.append("Todos OK")
    resumen = "\n".join(resumen_lines)
    print(f"[AutoTest] {resumen}")

    # Notificar solo el resumen vía WhatsApp (mensaje corto, evita problemas de sesión 24hs)
    phone = _normalize_phone(SANTIAGO_PHONE) if SANTIAGO_PHONE else ""
    if phone and WATI_API_URL and WATI_API_TOKEN:
        try:
            resp = http_requests.post(
                f"{WATI_API_URL.rstrip('/')}/api/v1/sendSessionMessage/{phone}",
                params={"messageText": resumen},
                headers={"Authorization": f"Bearer {WATI_API_TOKEN}"},
                timeout=10,
            )
            body = resp.json() if resp.ok else {}
            if resp.ok and body.get("result") is not False:
                print(f"[AutoTest] Resumen enviado a {phone}")
            else:
                print(f"[AutoTest] Session msg falló ({resp.status_code}) — solo en logs")
        except Exception as e:
            print(f"[AutoTest] Error enviando resumen: {e}")


_WABA_ID = "1512049110526718"

def _waba_health_check() -> None:
    """Re-suscribe el WABA al app cada hora — evita caídas silenciosas de 26hs."""
    if not WA_TOKEN:
        return
    try:
        resp = http_requests.post(
            f"https://graph.facebook.com/v20.0/{_WABA_ID}/subscribed_apps",
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
            timeout=10,
        )
        if resp.ok and resp.json().get("success"):
            print("[WABA health] Suscripción OK")
        else:
            print(f"[WABA health] ERROR: {resp.text[:200]}")
            tg_send("⚠️ *WABA health check falló* — revisar token WhatsApp en Railway")
    except Exception as e:
        print(f"[WABA health] {e}")

_template_status_cache: dict = {}

def _check_template_status() -> None:
    global _template_status_cache
    if not WATI_API_URL or not WATI_API_TOKEN:
        return
    templates_to_watch = {"recontacto_propiedad", "recontacto_general"}
    try:
        resp = http_requests.get(
            f"{WATI_API_URL.rstrip('/')}/api/v1/getMessageTemplates?pageSize=50",
            headers={"Authorization": f"Bearer {WATI_API_TOKEN}"},
            timeout=10,
        )
        if not resp.ok:
            return
        templates = resp.json().get("messageTemplates", [])
        for t in templates:
            name = t.get("elementName", "")
            status = t.get("status", "")
            if name not in templates_to_watch:
                continue
            prev = _template_status_cache.get(name)
            if prev is None:
                _template_status_cache[name] = status
                continue
            if status != prev:
                _template_status_cache[name] = status
                emoji = "✅" if status == "APPROVED" else "❌"
                tg_send(f"{emoji} Template *{name}* cambió a *{status}*.\n{'Listo para mandar el broadcast.' if status == 'APPROVED' else 'Revisar en Wati.'}")
                print(f"[Template check] {name}: {prev} → {status}")
    except Exception as e:
        print(f"[Template check] Error: {e}")

def _start_scheduler() -> None:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(timezone="America/Argentina/Buenos_Aires")
    # Cron fijo para que los redeploys no reseteen el timer
    scheduler.add_job(send_digest, "cron", hour="6,9,12,15,18,21", minute=0, kwargs={"hours": 3}, id="digest_3h")
    scheduler.add_job(meta_leads_reconcile, "cron", hour="0,6,12,18", minute=30, id="meta_reconcile_6h")
    scheduler.add_job(sofia_auto_test, "cron", hour="7,11,15,19,23", minute=0, id="sofia_autotest_4h")
    # Re-suscripción WABA cada hora — previene caída silenciosa de mensajes
    scheduler.add_job(_waba_health_check, "interval", minutes=60, id="waba_health")
    # Check estado templates cada 30 minutos — alerta cuando Meta aprueba/rechaza
    scheduler.add_job(_check_template_status, "interval", minutes=30, id="template_status")
    # Al arrancar: digest inmediato + re-suscripción WABA + check templates
    threading.Thread(target=lambda: send_digest(hours=6), daemon=True).start()
    threading.Thread(target=_waba_health_check, daemon=True).start()
    threading.Thread(target=_check_template_status, daemon=True).start()
    scheduler.start()
    print("[Scheduler] Digest + reconciliación Meta + prueba automática + WABA health + template check cada 30min")

# ── Entrypoint ─────────────────────────────────────────────────────────────────

# Arrancar scheduler siempre — tanto con Gunicorn (importa el módulo) como con python server.py
try:
    _start_scheduler()
except Exception as _sched_err:
    print(f"[Scheduler] ADVERTENCIA: no se pudo iniciar ({_sched_err}). El bot sigue funcionando, sin jobs periódicos.")

if __name__ == "__main__":
    print("=== Altavista Otero — Servidor Railway ===")
    print(f"Puerto: {PORT}")
    if WATI_API_URL and WATI_API_TOKEN:
        print(f"Sofía WhatsApp: Wati BSP ({WATI_API_URL})")
    elif WA_TOKEN and WA_PHONE_ID:
        print(f"Sofía WhatsApp: Meta Cloud API directo (sin Wati)")
    else:
        print(f"Sofía WhatsApp: SIN CREDENCIALES — bot inactivo")
    print(f"Anthropic: {'configurado' if ANTHROPIC_KEY else 'NO CONFIGURADO'}")
    print(f"Supabase sfre-web: {'OK' if SFRE_SUPABASE_URL else 'NO CONFIGURADO'}")
    app.run(host="0.0.0.0", port=PORT)
