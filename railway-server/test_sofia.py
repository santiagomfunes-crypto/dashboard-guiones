#!/usr/bin/env python3
"""
Test automático de Sofía — simula mensajes de WhatsApp contra el webhook real.
Uso: python3 test_sofia.py [--phone 5492494XXXXXX]
"""

import json
import time
import argparse
import requests
import os

RAILWAY_URL = "https://sofia-bot-production-e17d.up.railway.app"
# Teléfono de prueba (no tiene que ser real — los mensajes se guardan en Supabase igual)
DEFAULT_PHONE = "5490000000001"

SCENARIOS = [
    # (nombre, tipo, contenido)
    # ── Presentación y voseo ──────────────────────────────────────────────────
    ("01_saludo_inicial",           "text", "Hola"),
    ("02_pregunta_identidad_bot",   "text", "¿Sos un bot o una persona?"),

    # ── Calificación ─────────────────────────────────────────────────────────
    ("03_busqueda_vaga",            "text", "Busco un departamento"),
    ("04_zona_inexistente",         "text", "Busco algo en barrio Movediza, 2 dormitorios"),
    ("05_inversion",                "text", "Quiero invertir, ¿qué tienen disponible?"),

    # ── Garibaldi 431 ─────────────────────────────────────────────────────────
    ("06_garibaldi_general",        "text", "Me interesa Garibaldi 431"),
    ("07_garibaldi_piso4_frente",   "text", "Quiero ver el piso 4 al frente, el de precio especial"),
    ("08_ya_eligio_visita",         "text", "Sí, me interesa ese. ¿Cómo hago para verlo?"),

    # ── Objeciones ───────────────────────────────────────────────────────────
    ("09_precio_caro",              "text", "Me parece caro, vi algo más barato en otra inmobiliaria"),
    ("10_lo_pienso",                "text", "Lo voy a pensar"),

    # ── Roca 36 fideicomiso ───────────────────────────────────────────────────
    ("11_pregunta_fideicomiso",     "text", "Escuché que tienen un fideicomiso, ¿me contás?"),
    ("12_roca_36_directo",          "text", "Quiero info del proyecto Roca 36"),

    # ── Escalación ───────────────────────────────────────────────────────────
    ("13_pedir_santiago",           "text", "Quiero hablar con Santiago directamente"),

    # ── Idioma / voseo ───────────────────────────────────────────────────────
    ("14_respuesta_corta",          "text", "¿Cuál es el precio?"),
    ("15_negritas",                 "text", "¿Pueden darme todos los detalles del depto?"),

    # ── Ráfaga (debounce) ────────────────────────────────────────────────────
    # Estos 3 se mandan con delay mínimo → deben generar UNA sola respuesta
    ("16a_rafaga_1",                "text", "Hola"),
    ("16b_rafaga_2",                "text", "busco depto"),
    ("16c_rafaga_3",                "text", "1 dormitorio centro"),

    # ── Memoria ──────────────────────────────────────────────────────────────
    ("17_pregunta_nombre_sofia",    "text", "¿Cómo dijiste que te llamabas?"),
]

def make_payload(phone: str, msg_type: str, content: str) -> dict:
    if msg_type == "text":
        msg = {"from": phone, "type": "text", "text": {"body": content}, "id": f"test_{int(time.time())}"}
    else:
        msg = {"from": phone, "type": msg_type, "id": f"test_{int(time.time())}"}
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [msg]}}]}]
    }

def send(phone: str, msg_type: str, content: str) -> int:
    payload = make_payload(phone, msg_type, content)
    try:
        r = requests.post(f"{RAILWAY_URL}/whatsapp/webhook", json=payload, timeout=10)
        return r.status_code
    except Exception as e:
        print(f"  ERROR: {e}")
        return 0

def clear_lead(phone: str) -> None:
    """Borra el historial del teléfono de prueba antes de arrancar."""
    SB_URL = "https://bsvcorcwcijpvwzxjzgu.supabase.co"
    SB_KEY = os.environ.get("SFRE_SUPABASE_SERVICE_KEY", "")
    if not SB_KEY:
        print("  (sin SFRE_SUPABASE_SERVICE_KEY — no se limpia lead previo)")
        return
    # Buscar lead
    r = requests.get(f"{SB_URL}/rest/v1/chat_leads?phone=eq.{phone}&select=id",
                     headers={"Authorization": f"Bearer {SB_KEY}", "apikey": SB_KEY})
    leads = r.json()
    if not leads:
        return
    lead_id = leads[0]["id"]
    requests.delete(f"{SB_URL}/rest/v1/chat_messages?lead_id=eq.{lead_id}",
                    headers={"Authorization": f"Bearer {SB_KEY}", "apikey": SB_KEY})
    requests.patch(f"{SB_URL}/rest/v1/chat_leads?id=eq.{lead_id}",
                   headers={"Authorization": f"Bearer {SB_KEY}", "apikey": SB_KEY,
                             "Content-Type": "application/json"},
                   json={"status": "nuevo", "notas": None, "sofia_paused": False})
    print(f"  Lead {lead_id} limpiado ✓")

def run(phone: str, burst_delay: float = 0.3, normal_delay: float = 6.0) -> None:
    print(f"\n{'='*60}")
    print(f"  TEST SOFÍA — {RAILWAY_URL}")
    print(f"  Teléfono de prueba: {phone}")
    print(f"{'='*60}\n")

    print("Limpiando lead previo...")
    clear_lead(phone)
    print()

    for i, (name, msg_type, content) in enumerate(SCENARIOS):
        is_burst = name.startswith("16")
        delay = burst_delay if is_burst else normal_delay

        print(f"[{name}] → \"{content[:60]}\"")
        status = send(phone, msg_type, content)
        print(f"  Webhook: {status} | esperando {delay}s...")

        # Después del último mensaje de la ráfaga, esperar más para que procese
        if name == "16c_rafaga_3":
            print("  (fin de ráfaga — esperando 8s para que debounce dispare)")
            time.sleep(8)
        else:
            time.sleep(delay)

    print(f"\n{'='*60}")
    print("  TEST COMPLETO")
    print(f"  Revisá las respuestas en el dashboard:")
    print(f"  https://propiedades.santiagofunes.com.ar/admin/leads")
    print(f"  Y los logs de Railway:")
    print(f"  https://railway.com/project/aac6e7e8-b6e1-414a-9db6-33f2379ebd5c/service/2a77c850-3def-460c-8289-53369213b7e8")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", default=DEFAULT_PHONE, help="Teléfono de prueba (E.164 sin +)")
    args = parser.parse_args()
    run(args.phone)
