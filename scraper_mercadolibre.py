#!/usr/bin/env python3
"""
Scraper diario MercadoLibre Inmuebles → Supabase
Extrae propiedades en Tandil desde el HTML de MercadoLibre
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
from datetime import datetime, timezone
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-AR,es;q=0.9",
}

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
DELAY_BETWEEN_REQUESTS = 2  # segundos entre requests


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


# ── Scraping ──────────────────────────────────────────────────────────────────

def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} para {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None


def extract_thumbnail_map(html):
    """Extrae el mapa {MLA_ID: thumbnail_url} del JSON embebido en el HTML de ML."""
    thumb_map = {}
    # ML embute el estado de la página en un script _n.ctx.r={...}
    # que contiene cada item con su campo "thumbnail"
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
        # Extraer el JSON completo del POLYCARD usando balance de llaves
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

    # Indexar componentes por tipo
    comp_by_type = {}
    for c in components:
        comp_by_type[c.get("type")] = c

    # Título
    titulo = comp_by_type.get("title", {}).get("title", {}).get("text", "")

    # Tipología y operación desde headline
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

    # Precio (solo USD por ahora)
    precio_usd = None
    price_comp = comp_by_type.get("price", {}).get("price", {})
    current_price = price_comp.get("current_price", {})
    if current_price.get("currency") == "USD":
        precio_usd = current_price.get("value")

    # Atributos: ambientes, baños, m²
    dormitorios = None
    metros_totales = None
    cochera = False

    attrs = comp_by_type.get("attributes_list", {}).get("attributes_list", {}).get("texts", [])
    for attr in attrs:
        attr_lower = attr.lower()
        # Dormitorios / ambientes
        m = re.search(r"(\d+)\s+amb", attr_lower)
        if m:
            ambientes = int(m.group(1))
            dormitorios = max(0, ambientes - 1)  # ambientes = dormitorios + sala
        m = re.search(r"(\d+)\s+dorm", attr_lower)
        if m:
            dormitorios = int(m.group(1))
        # Metros cubiertos o totales
        m = re.search(r"([\d,.]+)\s*m²", attr_lower)
        if m:
            val_str = m.group(1).replace(",", ".")
            try:
                metros_totales = float(val_str)
            except ValueError:
                pass
        # Cochera
        if "cochera" in attr_lower:
            cochera = True

    # Zona: simplificada a "Tandil"
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
        "dormitorios": dormitorios,
        "metros_totales": metros_totales,
        "cochera": cochera,
        "titulo": titulo,
        "imagen_url": imagen_url,
    }


def has_next_page(html, next_offset):
    """Retorna True si el HTML contiene un link a la página con next_offset."""
    return f"_Desde_{next_offset}" in html


def scrape_all():
    """Scrapea todas las URLs configuradas y retorna lista de propiedades."""
    all_props = {}  # fuente_id → prop (dedup)

    for tipologia, operacion, base_url in SEARCH_URLS:
        print(f"\n→ Scrapeando {tipologia}/{operacion}...")
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            url = base_url if offset == 0 else f"{base_url}_Desde_{offset + 1}"
            print(f"  Página {page + 1}: {url}")

            html = fetch_html(url)
            if not html:
                break

            polycards = extract_polycards(html)
            print(f"  → {len(polycards)} polycards encontrados")

            if not polycards:
                break

            thumbnail_map = extract_thumbnail_map(html)

            for pc in polycards:
                prop = parse_polycard(pc, tipologia, operacion, thumbnail_map)
                if prop:
                    all_props[prop["fuente_id"]] = prop

            # Chequear si el HTML linkea a la siguiente página antes de pedirla
            next_offset = (page + 1) * PAGE_SIZE + 1
            if not has_next_page(html, next_offset):
                break

            if page < MAX_PAGES - 1:
                time.sleep(DELAY_BETWEEN_REQUESTS)

    return list(all_props.values())


# ── Supabase Upsert ────────────────────────────────────────────────────────────

def upsert_supabase(props, supabase_url, service_key, dry_run=False):
    """Hace upsert de las propiedades en Supabase."""
    if not props:
        print("\nNo hay propiedades para insertar.")
        return 0, 0

    now = datetime.now(timezone.utc).isoformat()

    # Agregar ultima_vez_visto a todos
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
            print(f"  {p['fuente_id']}: {p['titulo'][:60]} | {p['precio_usd']} USD")
        return len(props), 0

    # Upsert en lotes de 50
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
    parser.add_argument("--tipologia", help="Solo scrapear esta tipología (ej: departamento)")
    args = parser.parse_args()

    print(f"=== Scraper MercadoLibre Inmuebles ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en .env", file=sys.stderr)
        sys.exit(1)

    props = scrape_all()
    print(f"\nTotal propiedades scraped: {len(props)}")

    inserted, errors = upsert_supabase(props, supabase_url, service_key, dry_run=args.dry_run)

    print(f"\n=== Resultado ===")
    print(f"Upsertadas: {inserted}")
    print(f"Errores:    {errors}")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
