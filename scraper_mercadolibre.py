#!/usr/bin/env python3
"""
Scraper diario MercadoLibre Inmuebles → Supabase

Dos modos de extracción (auto-seleccionado):
  1. API oficial de ML (si ML_CLIENT_ID + ML_CLIENT_SECRET en .env) — sin anti-bot
  2. HTML scraping con curl + PoW solver (fallback) — soporta proxy vía ML_PROXY_URL

Uso: python3 scraper_mercadolibre.py
     python3 scraper_mercadolibre.py --dry-run
     python3 scraper_mercadolibre.py --mode api     # forzar modo API
     python3 scraper_mercadolibre.py --mode html    # forzar modo HTML
"""

import sys
import re
import json
import time
import random
import hashlib
import argparse
import subprocess
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, date
from pathlib import Path

# Normalización de zonas
try:
    from zona_utils import normalizar_zona
except ImportError:
    def normalizar_zona(zona, titulo, descripcion):
        return "Otros Tandil", False

# ── Configuración ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# URLs a scrapear: (tipologia, operacion, url_base)
SEARCH_URLS = [
    ("departamento", "venta",    "https://inmuebles.mercadolibre.com.ar/departamentos/venta/tandil/"),
    ("departamento", "alquiler", "https://inmuebles.mercadolibre.com.ar/departamentos/alquiler/tandil/"),
    ("casa",         "venta",    "https://inmuebles.mercadolibre.com.ar/casas/venta/tandil/"),
    ("casa",         "alquiler", "https://inmuebles.mercadolibre.com.ar/casas/alquiler/tandil/"),
    ("terreno",      "venta",    "https://inmuebles.mercadolibre.com.ar/terrenos/venta/tandil/"),
    ("ph",           "venta",    "https://inmuebles.mercadolibre.com.ar/ph/venta/tandil/"),
    ("local",        "alquiler", "https://inmuebles.mercadolibre.com.ar/locales/alquiler/tandil/"),
    ("oficina",      "alquiler", "https://inmuebles.mercadolibre.com.ar/oficinas/alquiler/tandil/"),
]

MAX_PAGES = 3          # máximo de páginas por combinación (48 items/página)
PAGE_SIZE = 48
DELAY_BETWEEN_PAGES = 5     # segundos entre páginas dentro de una categoría
DELAY_BETWEEN_CATEGORIES = 10  # segundos entre categorías (sesión nueva)
CURL_TIMEOUT = 20           # segundos timeout para curl

# ── ML API config ────────────────────────────────────────────────────────────
# Categorías ML para inmuebles en Argentina
ML_API_BASE = "https://api.mercadolibre.com"
ML_TOKEN_URL = f"{ML_API_BASE}/oauth/token"
ML_SEARCH_URL = f"{ML_API_BASE}/sites/MLA/search"
ML_API_LIMIT = 50  # max items por request API

# Mapeo tipologia → category_id de ML (subcategorías de MLA1459 Inmuebles)
ML_CATEGORY_MAP = {
    ("departamento", "venta"):    "MLA401685",   # Departamentos Venta
    ("departamento", "alquiler"): "MLA401695",   # Departamentos Alquiler
    ("casa",         "venta"):    "MLA401684",   # Casas Venta
    ("casa",         "alquiler"): "MLA401694",   # Casas Alquiler
    ("terreno",      "venta"):    "MLA401686",   # Terrenos Venta
    ("ph",           "venta"):    "MLA401687",   # PH Venta
    ("local",        "alquiler"): "MLA401700",   # Locales Alquiler
    ("oficina",      "alquiler"): "MLA401701",   # Oficinas Alquiler
}
# State ID para Buenos Aires (Tandil)
ML_STATE_BUENOS_AIRES = "TUxBUEJVRU5PNzZhOA"
# City ID para Tandil
ML_CITY_TANDIL = "TUxBQ1RBTmRhOQ"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


# ── Tipo de cambio ────────────────────────────────────────────────────────────

def get_dolar_blue():
    """Obtiene el tipo de cambio blue desde dolarapi.com. Retorna (compra, venta) o (None, None)."""
    url = "https://dolarapi.com/v1/dolares/blue"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("compra"), data.get("venta")
    except Exception as e:
        print(f"  Advertencia: no se pudo obtener cotización blue: {e}", file=sys.stderr)
        return None, None


# ── Carga de credenciales ──────────────────────────────────────────────────────

def load_env():
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


# ── ML API — Token management & search ────────────────────────────────────────

_ml_token_cache = {"access_token": None, "expires_at": 0}


def ml_get_token(client_id, client_secret):
    """Obtiene access_token via client_credentials grant. Cachea hasta expiración."""
    now = time.time()
    if _ml_token_cache["access_token"] and now < _ml_token_cache["expires_at"] - 60:
        return _ml_token_cache["access_token"]

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    req = urllib.request.Request(
        ML_TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            _ml_token_cache["access_token"] = body["access_token"]
            _ml_token_cache["expires_at"] = now + body.get("expires_in", 21600)
            print(f"  ML API token obtenido (expira en {body.get('expires_in', '?')}s)")
            return body["access_token"]
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:300]
        print(f"  Error obteniendo ML token: HTTP {e.code} — {err}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error obteniendo ML token: {e}", file=sys.stderr)
        return None


def ml_api_search(token, category_id, offset=0):
    """Busca inmuebles en Tandil via ML API. Retorna (results, total) o ([], 0)."""
    params = urllib.parse.urlencode({
        "category": category_id,
        "state": ML_STATE_BUENOS_AIRES,
        "city": ML_CITY_TANDIL,
        "limit": ML_API_LIMIT,
        "offset": offset,
    })
    url = f"{ML_SEARCH_URL}?{params}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            results = data.get("results", [])
            total = data.get("paging", {}).get("total", 0)
            return results, total
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:300]
        print(f"  Error ML API search: HTTP {e.code} — {err}", file=sys.stderr)
        return [], 0
    except Exception as e:
        print(f"  Error ML API search: {e}", file=sys.stderr)
        return [], 0


def parse_api_result(item, tipologia_default, operacion_default):
    """Convierte un resultado de la API de ML en dict para Supabase."""
    fuente_id = item.get("id", "")
    if not fuente_id or not fuente_id.startswith("MLA"):
        return None

    currency = item.get("currency_id", "")
    price = item.get("price")

    dormitorios = None
    metros_totales = None
    superficie_cubierta = None
    cochera = False

    for attr in item.get("attributes", []):
        attr_id = attr.get("id", "")
        val = attr.get("value_name", "") or ""
        if attr_id == "BEDROOMS" and val.isdigit():
            dormitorios = int(val)
        elif attr_id == "TOTAL_AREA":
            m = re.search(r"([\d,.]+)", val)
            if m:
                try:
                    metros_totales = float(m.group(1).replace(",", "."))
                except ValueError:
                    pass
        elif attr_id == "COVERED_AREA":
            m = re.search(r"([\d,.]+)", val)
            if m:
                try:
                    superficie_cubierta = float(m.group(1).replace(",", "."))
                except ValueError:
                    pass
        elif attr_id == "HAS_PARKING" and val.lower() in ("sí", "si", "yes"):
            cochera = True

    location = item.get("location", {})
    zona = location.get("neighborhood", {}).get("name") or location.get("city", {}).get("name") or "Tandil"

    return {
        "fuente": "mercadolibre",
        "fuente_id": fuente_id,
        "url": item.get("permalink", ""),
        "tipologia": tipologia_default,
        "operacion": operacion_default,
        "zona": zona,
        "precio_usd": price if currency == "USD" else None,
        "precio_ars": price if currency == "ARS" else None,
        "tipo_cambio_usd": None,
        "dormitorios": dormitorios,
        "metros_totales": metros_totales,
        "superficie_cubierta": superficie_cubierta,
        "cochera": cochera,
        "titulo": item.get("title", ""),
        "imagen_url": item.get("thumbnail", ""),
        "descripcion": "",
    }


def scrape_all_api(client_id, client_secret):
    """Extrae todas las propiedades via ML API oficial."""
    token = ml_get_token(client_id, client_secret)
    if not token:
        print("  No se pudo obtener token ML. Abortando modo API.", file=sys.stderr)
        return None  # None = señal para caer al fallback HTML

    all_props = {}
    search_items = list(ML_CATEGORY_MAP.items())
    random.shuffle(search_items)

    for cat_idx, ((tipologia, operacion), cat_id) in enumerate(search_items):
        print(f"\n→ API [{cat_idx + 1}/{len(search_items)}] {tipologia}/{operacion} (cat={cat_id})")

        offset = 0
        for page in range(MAX_PAGES):
            results, total = ml_api_search(token, cat_id, offset=offset)
            if not results:
                break

            print(f"  Página {page + 1}: {len(results)} resultados (total={total})")

            for item in results:
                prop = parse_api_result(item, tipologia, operacion)
                if prop:
                    all_props[prop["fuente_id"]] = prop

            offset += ML_API_LIMIT
            if offset >= total:
                break

            time.sleep(random.uniform(0.5, 1.5))

        # Pausa corta entre categorías (la API tiene rate limit ~30 req/min)
        if cat_idx < len(search_items) - 1:
            time.sleep(random.uniform(1, 3))

    print(f"\n  API: {len(all_props)} propiedades extraídas en total")
    return list(all_props.values())


# ── Extracción de datos del HTML ───────────────────────────────────────────────

def extract_thumbnail_map(html):
    """Extrae el mapa {MLA_ID: thumbnail_url} del JSON embebido en el HTML de ML."""
    thumb_map = {}
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for block in script_blocks:
        if '"thumbnail"' not in block or '"id":"MLA' not in block:
            continue
        for m in re.finditer(r'"id"\s*:\s*"(MLA\d+)"', block):
            mla_id = m.group(1)
            after = block[m.start():m.start() + 2000]
            thumb_m = re.search(r'"thumbnail"\s*:\s*"(http[^"]+)"', after)
            if thumb_m:
                raw = thumb_m.group(1).replace('\\u002F', '/').replace('\\/', '/')
                thumb_map[mla_id] = raw.replace('http://', 'https://', 1)
        if thumb_map:
            break
    return thumb_map


def extract_polycards(html):
    """Extrae todos los objetos POLYCARD del HTML de ML."""
    polycards = []
    pattern = re.compile(r'\{"id":"POLYCARD","state":"VISIBLE","polycard":\{')
    for match in pattern.finditer(html):
        start = match.start()
        depth = 0
        end = start
        for i, ch in enumerate(html[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            obj = json.loads(html[start:end])
            polycards.append(obj)
        except json.JSONDecodeError:
            pass
    return polycards


def parse_polycard(polycard, tipologia_default, operacion_default, thumbnail_map=None):
    """Convierte un POLYCARD en un dict listo para Supabase."""
    meta = polycard.get("polycard", {}).get("metadata", {})
    components = polycard.get("polycard", {}).get("components", [])

    fuente_id = meta.get("id", "")
    if not fuente_id or not fuente_id.startswith("MLA"):
        return None

    url_path = meta.get("url", "")
    url = f"https://{url_path}" if url_path and not url_path.startswith("http") else url_path

    comp_by_type = {}
    for c in components:
        comp_by_type[c.get("type")] = c

    titulo = comp_by_type.get("title", {}).get("title", {}).get("text", "")

    headline_text = comp_by_type.get("headline", {}).get("headline", {}).get("text", "").lower()
    tipologia = tipologia_default
    operacion = operacion_default
    if headline_text:
        if "venta" in headline_text:
            operacion = "venta"
        elif "alquiler" in headline_text:
            operacion = "alquiler"
        for t in ["departamento", "casa", "ph", "terreno", "local", "oficina", "cochera", "campo"]:
            if t in headline_text:
                tipologia = t
                break

    precio_usd = None
    precio_ars = None
    price_comp = comp_by_type.get("price", {}).get("price", {})
    current_price = price_comp.get("current_price", {})
    if current_price.get("currency") == "USD":
        precio_usd = current_price.get("value")
    elif current_price.get("currency") == "ARS":
        precio_ars = current_price.get("value")

    dormitorios = None
    metros_totales = None
    superficie_cubierta = None
    cochera = False

    attrs = comp_by_type.get("attributes_list", {}).get("attributes_list", {}).get("texts", [])
    for attr in attrs:
        attr_lower = attr.lower()
        m = re.search(r"(\d+)\s+amb", attr_lower)
        if m:
            ambientes = int(m.group(1))
            dormitorios = max(0, ambientes - 1)
        m = re.search(r"(\d+)\s+dorm", attr_lower)
        if m:
            dormitorios = int(m.group(1))
        # superficie cubierta: buscar "m² cub" o "cubiertos" antes de genérico
        mc = re.search(r"([\d,.]+)\s*m²\s*cub", attr_lower)
        if mc:
            val_str = mc.group(1).replace(",", ".")
            try:
                superficie_cubierta = float(val_str)
            except ValueError:
                pass
        elif re.search(r"([\d,.]+)\s*m²", attr_lower) and metros_totales is None:
            m2 = re.search(r"([\d,.]+)\s*m²", attr_lower)
            val_str = m2.group(1).replace(",", ".")
            try:
                metros_totales = float(val_str)
            except ValueError:
                pass
        if "cochera" in attr_lower:
            cochera = True

    zona = "Tandil"
    location_text = comp_by_type.get("location", {}).get("location", {}).get("text", "")
    if location_text:
        zona = location_text

    imagen_url = (thumbnail_map or {}).get(fuente_id)

    descripcion = ""
    desc_comp = comp_by_type.get("description", {}).get("description", {})
    if isinstance(desc_comp, dict):
        descripcion = desc_comp.get("text", "") or ""
    if not descripcion:
        # Fallback: buscar en attributes_list textos más largos (posibles descripciones)
        for attr in attrs:
            if len(attr) > 60:
                descripcion = attr
                break
    descripcion = descripcion[:500]

    return {
        "fuente": "mercadolibre",
        "fuente_id": fuente_id,
        "url": url,
        "tipologia": tipologia,
        "operacion": operacion,
        "zona": zona,
        "precio_usd": precio_usd,
        "precio_ars": precio_ars,
        "tipo_cambio_usd": None,
        "dormitorios": dormitorios,
        "metros_totales": metros_totales,
        "superficie_cubierta": superficie_cubierta,
        "cochera": cochera,
        "titulo": titulo,
        "imagen_url": imagen_url,
        "descripcion": descripcion,
    }


def has_next_page(html, next_offset):
    return f"_Desde_{next_offset}" in html


# ── Scraping con curl + PoW solver ───────────────────────────────────────────

MAX_RETRIES = 3


def _solve_pow(hash_prefix, difficulty):
    """Resuelve el proof-of-work SHA-256 de ML. Retorna el nonce."""
    target = "0" * difficulty
    for n in range(50_000_000):
        h = hashlib.sha256((hash_prefix + str(n)).encode()).hexdigest()
        if h.startswith(target):
            return n
    return 0


def _parse_bmstate(cookie_file):
    """Lee _bmstate del archivo de cookies curl y retorna (hash_prefix, difficulty)."""
    try:
        with open(cookie_file) as f:
            for line in f:
                if "_bmstate" in line:
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        decoded = urllib.parse.unquote(parts[-1])
                        bm_parts = decoded.split(";")
                        if len(bm_parts) >= 2:
                            return bm_parts[0], int(bm_parts[1])
    except Exception:
        pass
    return None, None


def _append_solved_cookies(cookie_file, hash_prefix, nonce):
    """Agrega las cookies resueltas al archivo de cookies curl."""
    bmc_value = urllib.parse.quote(f"{hash_prefix};{nonce}", safe="")
    with open(cookie_file, "a") as f:
        f.write(f".mercadolibre.com.ar\tTRUE\t/\tTRUE\t0\t_bmc\t{bmc_value}\n")
        f.write(f".mercadolibre.com.ar\tTRUE\t/\tTRUE\t0\t_bm_skipml\ttrue\n")


def _is_blocked(html):
    """Detecta si ML nos bloqueó con suspicious-traffic o account-verification."""
    check = html[:10000].lower()
    return ("suspicious-traffic" in check
            or "account-verification" in check
            or "gz/account-verification" in check)


def _build_curl_base(user_agent, proxy_url=None):
    """Arma el comando curl base con proxy opcional."""
    cmd = [
        "curl", "-s", "-L",
        "-H", f"User-Agent: {user_agent}",
        "-H", "Accept-Language: es-AR,es;q=0.9,en;q=0.8",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "--max-time", str(CURL_TIMEOUT),
    ]
    if proxy_url:
        cmd += ["--proxy", proxy_url]
    return cmd


def _create_session(url, user_agent, proxy_url=None):
    """Crea una sesión fresca: cookie file nuevo + resuelve PoW si aparece."""
    cookie_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="ml_cookies_", delete=False
    ).name

    curl_base = _build_curl_base(user_agent, proxy_url)

    # Request inicial para obtener challenge
    subprocess.run(
        curl_base + ["-c", cookie_file, url],
        capture_output=True, text=True, timeout=CURL_TIMEOUT + 10,
    )

    hash_prefix, difficulty = _parse_bmstate(cookie_file)
    if hash_prefix and difficulty is not None:
        print(f"    Session PoW: dificultad={difficulty}", end="")
        nonce = _solve_pow(hash_prefix, difficulty)
        print(f", nonce={nonce}")
        _append_solved_cookies(cookie_file, hash_prefix, nonce)
        time.sleep(random.uniform(1, 2))
    else:
        print("    Session: sin challenge PoW (posible bloqueo IP)")

    return cookie_file


def fetch_html_curl(url, cookie_file, user_agent, proxy_url=None):
    """Fetch HTML via curl con proxy opcional, detectando bloqueos de ML."""
    curl_base = _build_curl_base(user_agent, proxy_url)

    for attempt in range(MAX_RETRIES):
        # Backoff exponencial con jitter
        if attempt > 0:
            backoff = min(2 ** attempt + random.uniform(0, 2), 30)
            print(f"  Reintentando en {backoff:.0f}s (intento {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(backoff)

        result = subprocess.run(
            curl_base + ["-b", cookie_file, "-c", cookie_file, url],
            capture_output=True, text=True, timeout=CURL_TIMEOUT + 10,
        )
        html = result.stdout

        if not html or len(html) < 500:
            print(f"  ⚠ Respuesta vacía en {url} (intento {attempt + 1}/{MAX_RETRIES})", file=sys.stderr)
            continue

        # Detectar bloqueo suspicious-traffic (no reintentable con cookies)
        if _is_blocked(html):
            print(f"  ⚠ Bloqueado por suspicious-traffic en {url}")
            return None

        # Si es página de challenge PoW, resolver
        if "micro-landing" in html[:5000] or ("_bmstate" in html and "verifyChallenge" in html):
            hash_prefix, difficulty = _parse_bmstate(cookie_file)
            if hash_prefix and difficulty is not None:
                print(f"  → Challenge PoW detectado (dificultad={difficulty}), resolviendo...")
                nonce = _solve_pow(hash_prefix, difficulty)
                print(f"  → Resuelto: nonce={nonce}")
                _append_solved_cookies(cookie_file, hash_prefix, nonce)
                result2 = subprocess.run(
                    curl_base + ["-b", cookie_file, "-c", cookie_file, url],
                    capture_output=True, text=True, timeout=CURL_TIMEOUT + 10,
                )
                html = result2.stdout
                if html and len(html) > 5000 and "micro-landing" not in html[:5000] and not _is_blocked(html):
                    return html
                print(f"  ⚠ Challenge resuelto pero página sigue bloqueada (intento {attempt + 1})", file=sys.stderr)
            else:
                print(f"  ⚠ Challenge detectado pero no se pudo parsear _bmstate", file=sys.stderr)
            continue

        return html

    return None


def scrape_all_html(proxy_url=None):
    """Scrapea todas las URLs configuradas via HTML + PoW solver.

    Usa sesiones frescas por categoría para evitar detección de suspicious-traffic.
    ML detecta patrones de navegación cross-categoría con la misma sesión.
    Soporta proxy vía ML_PROXY_URL en .env.
    """
    if proxy_url:
        print(f"  Usando proxy: {proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url}")

    all_props = {}  # fuente_id → prop (dedup)
    cookie_files = []  # para limpieza al final
    blocked_count = 0

    # Randomizar orden de categorías para no siempre empezar igual
    search_urls = list(SEARCH_URLS)
    random.shuffle(search_urls)

    for cat_idx, (tipologia, operacion, base_url) in enumerate(search_urls):
        # User agent diferente por categoría
        user_agent = random.choice(USER_AGENTS)

        print(f"\n→ HTML [{cat_idx + 1}/{len(search_urls)}] Scrapeando {tipologia}/{operacion}...")

        # Sesión fresca para cada categoría
        print(f"  Creando sesión fresca...")
        cookie_file = _create_session(base_url, user_agent, proxy_url)
        cookie_files.append(cookie_file)

        category_blocked = False
        for pg_idx in range(MAX_PAGES):
            offset = pg_idx * PAGE_SIZE
            url = base_url if offset == 0 else f"{base_url}_Desde_{offset + 1}"
            print(f"  Página {pg_idx + 1}: {url}")

            html = fetch_html_curl(url, cookie_file, user_agent, proxy_url)
            if not html:
                category_blocked = True
                break

            polycards = extract_polycards(html)
            print(f"  → {len(polycards)} polycards encontrados")

            if not polycards:
                alt_count = _try_extract_from_preloaded(html, all_props, tipologia, operacion)
                if alt_count == 0:
                    print(f"  Sin resultados en esta página, cortando paginación")
                    break
                continue

            thumbnail_map = extract_thumbnail_map(html)

            for pc in polycards:
                prop = parse_polycard(pc, tipologia, operacion, thumbnail_map)
                if prop:
                    all_props[prop["fuente_id"]] = prop

            next_offset = (pg_idx + 1) * PAGE_SIZE + 1
            if not has_next_page(html, next_offset):
                break

            if pg_idx < MAX_PAGES - 1:
                time.sleep(random.uniform(DELAY_BETWEEN_PAGES, DELAY_BETWEEN_PAGES * 1.8))

        if category_blocked:
            blocked_count += 1
            if blocked_count >= 3:
                print(f"\n⚠ {blocked_count} categorías bloqueadas en total, IP probablemente marcada. Cortando.")
                break
        else:
            blocked_count = max(0, blocked_count - 1)  # éxito reduce la cuenta

        # Pausa entre categorías
        if cat_idx < len(search_urls) - 1:
            delay = random.uniform(DELAY_BETWEEN_CATEGORIES, DELAY_BETWEEN_CATEGORIES * 1.5)
            print(f"  Esperando {delay:.0f}s antes de siguiente categoría...")
            time.sleep(delay)

    # Limpiar cookie files
    for cf in cookie_files:
        try:
            Path(cf).unlink()
        except Exception:
            pass

    if blocked_count > 0:
        print(f"\n⚠ {blocked_count}/{len(search_urls)} categorías fueron bloqueadas por ML")

    return list(all_props.values())


def _try_extract_from_preloaded(html, all_props, tipologia, operacion):
    """
    Extracción alternativa desde window.__PRELOADED_STATE__ o similar JSON embebido.
    Retorna la cantidad de items extraídos.
    """
    count = 0
    # Buscar resultados en __PRELOADED_STATE__
    m = re.search(r'window\.__PRELOADED_STATE__\s*=\s*(\{.+?\});\s*</script>', html, re.DOTALL)
    if not m:
        # Buscar en script type="application/ld+json"
        ld_blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for block in ld_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        prop = _parse_ld_item(item, tipologia, operacion)
                        if prop:
                            all_props[prop["fuente_id"]] = prop
                            count += 1
            except Exception:
                pass
        return count

    try:
        state = json.loads(m.group(1))
        results = (
            state.get("initialState", {})
                 .get("results", [])
        )
        for item in results:
            prop = _parse_preloaded_item(item, tipologia, operacion)
            if prop:
                all_props[prop["fuente_id"]] = prop
                count += 1
    except Exception:
        pass

    return count


def _parse_preloaded_item(item, tipologia, operacion):
    """Parsea un item del __PRELOADED_STATE__."""
    fuente_id = item.get("id", "")
    if not fuente_id or not fuente_id.startswith("MLA"):
        return None
    currency = item.get("currency_id")
    raw_price = item.get("price")
    return {
        "fuente": "mercadolibre",
        "fuente_id": fuente_id,
        "url": item.get("permalink", ""),
        "tipologia": tipologia,
        "operacion": operacion,
        "zona": item.get("location", {}).get("city_name", "Tandil"),
        "precio_usd": raw_price if currency == "USD" else None,
        "precio_ars": raw_price if currency == "ARS" else None,
        "tipo_cambio_usd": None,
        "dormitorios": None,
        "metros_totales": None,
        "cochera": False,
        "titulo": item.get("title", ""),
        "imagen_url": item.get("thumbnail", ""),
        "descripcion": "",
    }


def _parse_ld_item(item, tipologia, operacion):
    """Parsea un item de JSON-LD."""
    url = item.get("url", "")
    fuente_id = ""
    m = re.search(r'MLA(\d+)', url)
    if m:
        fuente_id = f"MLA{m.group(1)}"
    if not fuente_id:
        return None
    return {
        "fuente": "mercadolibre",
        "fuente_id": fuente_id,
        "url": url,
        "tipologia": tipologia,
        "operacion": operacion,
        "zona": "Tandil",
        "precio_usd": None,
        "precio_ars": None,
        "tipo_cambio_usd": None,
        "dormitorios": None,
        "metros_totales": None,
        "cochera": False,
        "titulo": item.get("name", ""),
        "imagen_url": item.get("image", ""),
        "descripcion": "",
    }


# ── Zona normalizada ───────────────────────────────────────────────────────────

def enrich_with_zona(props):
    """Agrega zona_normalizada y fuera_de_tandil a cada propiedad."""
    for p in props:
        zona_norm, fuera = normalizar_zona(
            p.get("zona") or "",
            p.get("titulo") or "",
            p.get("descripcion") or "",
        )
        p["zona_normalizada"] = zona_norm
        p["fuera_de_tandil"] = fuera


# ── Historial de precios ───────────────────────────────────────────────────────

def fetch_existing_prices(fuente_ids, supabase_url, service_key):
    """
    Retorna dict {fuente_id: {id, precio_usd}} para propiedades ya existentes en DB.
    Solo para fuente='mercadolibre'.
    """
    if not fuente_ids:
        return {}

    result = {}
    # Supabase soporta fuente_id=in.(id1,id2,...) en el query string
    batch_size = 100
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
    }

    for i in range(0, len(fuente_ids), batch_size):
        batch = fuente_ids[i: i + batch_size]
        ids_str = ",".join(batch)
        url = (
            f"{supabase_url}/rest/v1/propiedades_mercado"
            f"?select=id,fuente_id,precio_usd"
            f"&fuente=eq.mercadolibre"
            f"&fuente_id=in.({ids_str})"
            f"&limit={batch_size}"
        )
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                rows = json.loads(resp.read())
                for row in rows:
                    result[row["fuente_id"]] = {
                        "id": row["id"],
                        "precio_usd": row["precio_usd"],
                    }
        except Exception as e:
            print(f"  Advertencia: no se pudo leer precios existentes: {e}", file=sys.stderr)

    return result


def register_price_changes(props, existing_prices, supabase_url, service_key):
    """
    Compara precios nuevos con los existentes y registra cambios en propiedades_precio_historial.
    Solo loguea propiedades que ya existían en DB (las nuevas no tienen precio anterior).
    """
    historial_rows = []
    hoy = date.today().isoformat()

    for p in props:
        fid = p.get("fuente_id")
        nuevo_precio = p.get("precio_usd")
        existing = existing_prices.get(fid)

        if not existing or nuevo_precio is None:
            continue

        precio_anterior = existing.get("precio_usd")
        if precio_anterior is None or precio_anterior == nuevo_precio:
            continue

        historial_rows.append({
            "propiedad_id": existing["id"],
            "precio_usd": nuevo_precio,
            "fecha": hoy,
            "fuente": "mercadolibre",
        })

    if not historial_rows:
        return 0

    api_url = f"{supabase_url}/rest/v1/propiedades_precio_historial"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    body = json.dumps(historial_rows).encode("utf-8")
    req = urllib.request.Request(api_url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30):
            print(f"  Historial: {len(historial_rows)} cambios de precio registrados ✓")
            return len(historial_rows)
    except urllib.error.HTTPError as e:
        print(f"  Error historial {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"  Error historial: {e}", file=sys.stderr)
    return 0


# ── Supabase Upsert ────────────────────────────────────────────────────────────

def upsert_supabase(props, supabase_url, service_key, dry_run=False):
    """Hace upsert de las propiedades en Supabase."""
    if not props:
        print("\nNo hay propiedades para insertar.")
        return 0, 0

    now = datetime.now(timezone.utc).isoformat()

    for p in props:
        p["ultima_vez_visto"] = now

    api_url = f"{supabase_url}/rest/v1/propiedades_mercado?on_conflict=fuente,fuente_id"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    if dry_run:
        print(f"\n[DRY RUN] Se insertarían/actualizarían {len(props)} propiedades")
        print("Muestra (primeras 3):")
        for p in props[:3]:
            precio_str = (f"USD {p['precio_usd']}" if p.get("precio_usd")
                          else f"ARS {p.get('precio_ars')} → USD {p.get('precio_usd')}")
            print(f"  {p['fuente_id']}: {p['titulo'][:60]} | {precio_str} | zona={p.get('zona_normalizada')}")
        return len(props), 0

    batch_size = 50
    inserted = 0
    errors = 0

    for i in range(0, len(props), batch_size):
        batch = props[i : i + batch_size]
        body = json.dumps(batch).encode("utf-8")
        req = urllib.request.Request(api_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                inserted += len(batch)
                print(f"  Lote {i//batch_size + 1}: {len(batch)} propiedades upsertadas ✓")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(f"  Error HTTP {e.code} en lote {i//batch_size + 1}: {error_body}", file=sys.stderr)
            errors += len(batch)
        except Exception as e:
            print(f"  Error en lote {i//batch_size + 1}: {e}", file=sys.stderr)
            errors += len(batch)

    return inserted, errors


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper MercadoLibre Inmuebles → Supabase")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en Supabase")
    parser.add_argument("--mode", choices=["auto", "api", "html"], default="auto",
                        help="Modo de extracción: auto (API si hay creds, sino HTML), api, html")
    args = parser.parse_args()

    print(f"=== Scraper MercadoLibre Inmuebles ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en .env", file=sys.stderr)
        sys.exit(1)

    # Credenciales ML API (opcionales)
    ml_client_id = env.get("ML_CLIENT_ID")
    ml_client_secret = env.get("ML_CLIENT_SECRET")
    ml_proxy_url = env.get("ML_PROXY_URL")  # ej: http://user:pass@proxy.brightdata.com:22225
    has_api_creds = bool(ml_client_id and ml_client_secret)

    # Decidir modo de extracción
    mode = args.mode
    if mode == "auto":
        mode = "api" if has_api_creds else "html"
    elif mode == "api" and not has_api_creds:
        print("ERROR: --mode api requiere ML_CLIENT_ID y ML_CLIENT_SECRET en .env", file=sys.stderr)
        sys.exit(1)

    print(f"Modo: {mode}" + (f" | Proxy: {'sí' if ml_proxy_url else 'no'}" if mode == "html" else ""))

    # ── Extracción ──
    props = None

    if mode == "api":
        print("\n── Extrayendo via ML API oficial ──")
        props = scrape_all_api(ml_client_id, ml_client_secret)
        if props is None:
            print("  API falló. Cayendo a modo HTML como fallback...")
            mode = "html"

    if mode == "html":
        print("\n── Extrayendo via HTML scraping ──")
        props = scrape_all_html(proxy_url=ml_proxy_url)

    if props is None:
        props = []

    print(f"\nTotal propiedades scraped: {len(props)}")

    if not props:
        print("⚠ Sin propiedades extraídas. Abortando sin tocar DB.")
        sys.exit(1)

    # Obtener cotización blue y convertir precios ARS → USD
    dolar_compra, dolar_venta = get_dolar_blue()
    if dolar_venta:
        print(f"Dólar blue: compra ${dolar_compra} / venta ${dolar_venta}")
        convertidas = 0
        for p in props:
            if p.get("precio_ars") and not p.get("precio_usd"):
                p["precio_usd"] = round(p["precio_ars"] / dolar_venta, 2)
                p["tipo_cambio_usd"] = dolar_venta
                convertidas += 1
        print(f"Propiedades convertidas ARS→USD: {convertidas}")
    else:
        print("Advertencia: cotización blue no disponible, precios ARS no convertidos")

    # Enriquecer con zona_normalizada
    enrich_with_zona(props)

    # Leer precios existentes antes del upsert (para detectar cambios)
    existing_prices = {}
    if not args.dry_run:
        print("Leyendo precios existentes para historial...")
        fuente_ids = [p["fuente_id"] for p in props]
        existing_prices = fetch_existing_prices(fuente_ids, supabase_url, service_key)
        print(f"  {len(existing_prices)} propiedades ya existentes en DB")

    inserted, errors = upsert_supabase(props, supabase_url, service_key, dry_run=args.dry_run)

    # Registrar cambios de precio en historial
    if not args.dry_run and existing_prices:
        register_price_changes(props, existing_prices, supabase_url, service_key)

    print(f"\n=== Resultado ===")
    print(f"Modo usado: {mode}")
    print(f"Upsertadas: {inserted}")
    print(f"Errores:    {errors}")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
