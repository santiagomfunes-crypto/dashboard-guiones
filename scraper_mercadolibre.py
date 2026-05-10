#!/usr/bin/env python3
"""
Scraper diario MercadoLibre Inmuebles → Supabase
Extrae propiedades en Tandil desde MercadoLibre con Playwright (renderiza JS)
y hace upsert en la tabla propiedades_mercado.

Uso: python3 scraper_mercadolibre.py
     python3 scraper_mercadolibre.py --dry-run
"""

import sys
import re
import json
import time
import argparse
import urllib.request
import urllib.error
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
DELAY_BETWEEN_REQUESTS = 3  # segundos entre requests (más tiempo para JS)
PAGE_LOAD_TIMEOUT = 20000   # ms timeout para carga inicial
PAGE_JS_WAIT = 8            # segundos de espera para que el JS renderice los resultados


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
        m = re.search(r"([\d,.]+)\s*m²", attr_lower)
        if m:
            val_str = m.group(1).replace(",", ".")
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
        "cochera": cochera,
        "titulo": titulo,
        "imagen_url": imagen_url,
    }


def has_next_page(html, next_offset):
    return f"_Desde_{next_offset}" in html


# ── Scraping con Playwright ────────────────────────────────────────────────────

def fetch_html_playwright(page, url):
    """Usa una página Playwright ya abierta para navegar y obtener el HTML."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        # Esperar que el JS renderice los resultados (supera el micro-landing challenge)
        time.sleep(PAGE_JS_WAIT)
        # set_default_timeout garantiza que page.content() no cuelgue indefinidamente
        page.set_default_timeout(PAGE_LOAD_TIMEOUT)
        return page.content()
    except Exception as e:
        print(f"  Error Playwright en {url}: {e}", file=sys.stderr)
        return None


def scrape_all():
    """Scrapea todas las URLs configuradas y retorna lista de propiedades."""
    from playwright.sync_api import sync_playwright
    try:
        from playwright_stealth import Stealth
        _stealth = Stealth(
            navigator_webdriver=True,
            navigator_platform_override="MacIntel",
        )
    except ImportError:
        _stealth = None

    all_props = {}  # fuente_id → prop (dedup)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
            viewport={"width": 1280, "height": 800},
        )
        # Ocultar flag WebDriver que ML detecta para el anti-bot challenge
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()
        if _stealth:
            _stealth.apply_stealth_sync(page)
            print("  [stealth mode activo]")

        for tipologia, operacion, base_url in SEARCH_URLS:
            print(f"\n→ Scrapeando {tipologia}/{operacion}...")
            for pg_idx in range(MAX_PAGES):
                offset = pg_idx * PAGE_SIZE
                url = base_url if offset == 0 else f"{base_url}_Desde_{offset + 1}"
                print(f"  Página {pg_idx + 1}: {url}")

                html = fetch_html_playwright(page, url)
                if not html:
                    break

                polycards = extract_polycards(html)
                print(f"  → {len(polycards)} polycards encontrados")

                if not polycards:
                    # Intentar extraer via JSON embebido alternativo
                    # ML a veces embebe los items en window.__PRELOADED_STATE__
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
                    time.sleep(DELAY_BETWEEN_REQUESTS)

        browser.close()

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
    args = parser.parse_args()

    print(f"=== Scraper MercadoLibre Inmuebles (Playwright) ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en .env", file=sys.stderr)
        sys.exit(1)

    props = scrape_all()
    print(f"\nTotal propiedades scraped: {len(props)}")

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
    print(f"Upsertadas: {inserted}")
    print(f"Errores:    {errors}")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
