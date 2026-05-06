#!/usr/bin/env python3
"""
Stress test continuo de Sofía — corre por horas con múltiples usuarios simultáneos.
Uso: python3 stress_sofia.py
Logs: stress_sofia.log
"""

import json
import time
import random
import threading
import requests
import datetime
import signal
import sys
from collections import defaultdict

RAILWAY_URL = "https://sofia-bot-production-e17d.up.railway.app"
LOG_FILE    = "stress_sofia.log"
RUNNING     = True

# ── Teléfonos ficticios (usuarios simultáneos) ────────────────────────────────
PHONES = [
    "5490000000101",  # Usuario A — comprador serio
    "5490000000102",  # Usuario B — inversor
    "5490000000103",  # Usuario C — curioso / frío
    "5490000000104",  # Usuario D — agresivo / objeciones
    "5490000000105",  # Usuario E — ráfagas de mensajes
    "5490000000106",  # Usuario F — pregunta todo sobre Roca
    "5490000000107",  # Usuario G — mezcla idiomas raros
    "5490000000108",  # Usuario H — mensajes muy cortos
    "5490000000109",  # Usuario I — mensajes muy largos
    "5490000000110",  # Usuario J — escalación inmediata
]

# ── Banco de mensajes por categoría ──────────────────────────────────────────
SALUDOS = [
    "Hola", "Buenas", "Buen día", "Hola buenas tardes", "Holas",
    "Hola! Cómo están?", "Buenas noches", "Hola hay alguien?",
    "Holaa", "Buen dia, consulta",
]

GARIBALDI = [
    "Quiero info de Garibaldi 431",
    "Me interesa el depto de Garibaldi",
    "Vi la publicación de Garibaldi, ¿cuánto sale?",
    "El piso 4 al frente de Garibaldi, ¿está disponible?",
    "Quiero ver el departamento de Garibaldi 431 piso 4",
    "Garibaldi cuarto A, ¿qué precio tiene?",
    "¿Cuánto sale el de Garibaldi al frente?",
    "Me mandaron el link de Garibaldi 431, ¿me podés contar más?",
    "Garibaldi piso 4 frente, el de precio especial",
    "Vi que tienen un depto en Garibaldi en oferta",
]

ROCA = [
    "Me interesa el fideicomiso",
    "¿Qué es eso del proyecto Roca?",
    "Quiero info del fideicomiso Roca 36",
    "Proyecto roca, ¿cómo funciona el fideicomiso?",
    "¿Cuánto sale entrar al fideicomiso?",
    "Roca 36, ¿qué tienen?",
    "Me comentaron del fideicomiso de Santiago, ¿me contás?",
    "¿Tienen algo en construcción al costo?",
    "¿Cómo es lo del fideicomiso al costo?",
    "Proyecto Roca cuánto sale la entrada",
]

BUSQUEDAS_GENERALES = [
    "Busco departamento de 1 dormitorio en el centro",
    "Necesito algo para invertir, ¿qué me recomendás?",
    "Estoy buscando depto para vivir",
    "¿Tienen algo en zona centro?",
    "Busco algo chico, soy solo yo",
    "Quiero comprar un departamento en Tandil",
    "¿Qué propiedades tienen disponibles?",
    "Busco depto de un ambiente o uno dormitorio",
    "¿Tienen algo entre 80 y 120 mil dólares?",
    "Busco para entrar a vivir en 3 meses",
]

OBJECIONES = [
    "Me parece caro",
    "Vi algo más barato en otra inmobiliaria",
    "¿No hay descuento?",
    "No tengo el dinero ahora",
    "Lo voy a pensar",
    "Mi mujer todavía no lo vio",
    "¿Cuánto flexibilizan el precio?",
    "No me convence, es muy caro para esa zona",
    "Vi uno en Argenprop más barato",
    "Capaz en unos meses me animo",
]

IDENTIDAD = [
    "¿Sos un bot?",
    "¿Sos una IA?",
    "¿Hay una persona del otro lado?",
    "¿Esto es automático?",
    "¿Con quién hablo?",
    "¿Sos real?",
    "¿Me estás respondiendo vos o es una máquina?",
    "¿Cómo te llamás?",
    "¿Quién sos vos exactamente?",
    "¿Sos de la inmobiliaria?",
]

ESCALACION = [
    "Quiero hablar con Santiago",
    "¿Puedo hablar con el dueño?",
    "Pasame con alguien que me pueda dar el precio final",
    "Necesito hablar con un humano",
    "¿Puedo llamar a Santiago directamente?",
]

EDGE_CASES = [
    # Muy cortos
    "Sí", "No", "Dale", "Ok", "?", "...", "Bien",
    # Muy largos
    "Hola buen día, te escribo porque estoy buscando un departamento para comprar en Tandil, soy de Buenos Aires y estamos pensando en mudarnos allá con mi familia, tenemos dos nenes chicos y necesitamos algo con al menos un dormitorio grande, idealmente cerca del centro o de una plaza, con buena luz, que no sea muy oscuro, y que tenga estacionamiento o cochera cerca porque tenemos auto. El presupuesto es de hasta 120 mil dólares pero podemos hablar. ¿Qué tenés disponible?",
    # Mezcla idiomas
    "Hello, I'm looking for a property in Tandil",
    "Hola, busco depto, what do you have?",
    # Caracteres especiales
    "Hola! Busco depto 🏠 en Tandil... ¿tenés algo?",
    "BUSCO DEPTO URGENTE!!!",
    "Buenas... tengo una consulta 🤔",
    # Preguntas múltiples en un mensaje
    "¿Cuánto sale Garibaldi? ¿Y el fideicomiso? ¿Tienen cocheras?",
    "¿Podés mandarme fotos? ¿Cuándo puedo visitarlo? ¿Hay expensas?",
    # Temas de finanzas
    "¿Se puede pagar en pesos?",
    "¿Aceptan cuotas?",
    "¿Financian algo?",
    "¿Cuánto son las expensas?",
    "¿El precio es negociable?",
]

VISITA = [
    "Quiero visitarlo",
    "¿Cuándo puedo ir a verlo?",
    "Me gustaría coordinar una visita",
    "¿Puedo ir este finde?",
    "¿Está libre para ver mañana?",
    "Sí, me interesa verlo",
    "Dale, coordinemos la visita",
    "¿A qué hora puedo ir?",
]

ALL_MESSAGES = (
    SALUDOS + GARIBALDI + ROCA + BUSQUEDAS_GENERALES +
    OBJECIONES + IDENTIDAD + ESCALACION + EDGE_CASES + VISITA
)

# ── Perfiles de usuario (comportamientos) ─────────────────────────────────────
PROFILES = {
    "5490000000101": {"name": "Comprador serio",  "pool": GARIBALDI + VISITA + OBJECIONES, "delay": (5, 15), "burst": False},
    "5490000000102": {"name": "Inversor",         "pool": ROCA + BUSQUEDAS_GENERALES,      "delay": (8, 20), "burst": False},
    "5490000000103": {"name": "Curioso frío",     "pool": BUSQUEDAS_GENERALES + OBJECIONES,"delay": (15, 30),"burst": False},
    "5490000000104": {"name": "Objeciones",       "pool": OBJECIONES + ESCALACION,          "delay": (5, 12), "burst": False},
    "5490000000105": {"name": "Ráfagas",          "pool": ALL_MESSAGES,                     "delay": (0.5, 2),"burst": True},
    "5490000000106": {"name": "Roca fanático",    "pool": ROCA,                              "delay": (6, 18), "burst": False},
    "5490000000107": {"name": "Edge cases",       "pool": EDGE_CASES,                        "delay": (4, 10), "burst": False},
    "5490000000108": {"name": "Mensajes cortos",  "pool": ["Sí","No","Dale","Ok","¿?","...","Cuánto","Dónde","Cuándo"], "delay": (3, 8), "burst": False},
    "5490000000109": {"name": "Mensajes largos",  "pool": [m for m in EDGE_CASES if len(m) > 100], "delay": (10, 25), "burst": False},
    "5490000000110": {"name": "Escalador",        "pool": SALUDOS + ESCALACION + IDENTIDAD,  "delay": (4, 10), "burst": False},
}

# ── Logging ───────────────────────────────────────────────────────────────────
stats = defaultdict(lambda: {"sent": 0, "ok": 0, "err": 0})
lock  = threading.Lock()

def log(msg: str) -> None:
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def make_payload(phone: str, text: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [{
            "from": phone,
            "type": "text",
            "text": {"body": text},
            "id": f"stress_{int(time.time() * 1000)}"
        }]}}]}]
    }

def send_message(phone: str, text: str) -> bool:
    try:
        r = requests.post(
            f"{RAILWAY_URL}/whatsapp/webhook",
            json=make_payload(phone, text),
            timeout=8,
        )
        return r.status_code == 200
    except Exception:
        return False

# ── Worker por usuario ────────────────────────────────────────────────────────
def user_worker(phone: str) -> None:
    profile  = PROFILES.get(phone, {"name": phone, "pool": ALL_MESSAGES, "delay": (5, 15), "burst": False})
    name     = profile["name"]
    pool     = profile["pool"]
    min_d, max_d = profile["delay"]
    burst    = profile["burst"]

    log(f"▶ [{name}] Iniciando")

    # Primer mensaje siempre un saludo
    send_message(phone, random.choice(SALUDOS))
    time.sleep(random.uniform(min_d, max_d))

    round_num = 0
    while RUNNING:
        round_num += 1
        msg = random.choice(pool)

        if burst and random.random() < 0.4:
            # Mandar ráfaga de 2-4 mensajes rápidos
            burst_msgs = random.sample(pool, min(random.randint(2, 4), len(pool)))
            for bm in burst_msgs:
                ok = send_message(phone, bm)
                with lock:
                    stats[phone]["sent"] += 1
                    if ok: stats[phone]["ok"] += 1
                    else:  stats[phone]["err"] += 1
                log(f"  [{name}] BURST → \"{bm[:50]}\" {'✓' if ok else '✗'}")
                time.sleep(random.uniform(0.3, 1.2))
            time.sleep(random.uniform(6, 10))  # esperar que debounce resuelva
        else:
            ok = send_message(phone, msg)
            with lock:
                stats[phone]["sent"] += 1
                if ok: stats[phone]["ok"] += 1
                else:  stats[phone]["err"] += 1
            log(f"  [{name}] [{round_num}] → \"{msg[:60]}\" {'✓' if ok else '✗'}")
            delay = random.uniform(min_d, max_d)
            time.sleep(delay)

def stats_reporter() -> None:
    while RUNNING:
        time.sleep(60)
        with lock:
            total_sent = sum(s["sent"] for s in stats.values())
            total_ok   = sum(s["ok"]   for s in stats.values())
            total_err  = sum(s["err"]  for s in stats.values())
        log(f"\n{'─'*50}")
        log(f"  REPORTE — enviados: {total_sent} | ok: {total_ok} | err: {total_err}")
        for phone, s in stats.items():
            name = PROFILES.get(phone, {}).get("name", phone[-4:])
            log(f"    {name}: {s['sent']} msgs, {s['err']} errores")
        log(f"{'─'*50}\n")

def handle_exit(sig, frame):
    global RUNNING
    log("\n⏹ Deteniendo stress test...")
    RUNNING = False
    sys.exit(0)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    signal.signal(signal.SIGINT,  handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    log("="*50)
    log(f"  STRESS TEST SOFÍA — {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log(f"  {len(PHONES)} usuarios simultáneos")
    log(f"  {len(ALL_MESSAGES)} mensajes en el banco")
    log(f"  Logs: {LOG_FILE}")
    log("="*50 + "\n")

    # Lanzar workers con offset para no pegar todos juntos
    threads = []
    for i, phone in enumerate(PHONES):
        t = threading.Thread(target=user_worker, args=[phone], daemon=True)
        threads.append(t)
        t.start()
        time.sleep(random.uniform(1, 3))  # stagger el inicio

    # Reporter de stats cada 60s
    reporter = threading.Thread(target=stats_reporter, daemon=True)
    reporter.start()

    log(f"Todos los workers activos. Ctrl+C para detener.\n")

    # Mantener vivo
    while RUNNING:
        time.sleep(1)
