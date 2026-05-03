#!/usr/bin/env python3
"""
Scraper diario ArgEnProp → Supabase
Extrae propiedades en Tandil desde argenprop.com
y hace upsert en la tabla propiedades_mercado.

Referencia: SAN-241 (pivot desde mipropiedades.com.ar — dominio NXDOMAIN)

Uso: python3 scraper_argenprop.py
     python3 scraper_argenprop.py --dry-run
     python3 scraper_argenprop.py --max-pages 5
"""

import sys
import re
import json
import time
import argparse
import urllib.request
import urllib.error
import html as html_module
from datetime import datetime, timezone
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

BASE_URL = "https://www.argenprop.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

# Combinaciones a scrapear: (tipologia_db, operacion, path_base)
SEARCH_CONFIGS = [
    ("departamento", "venta",    "/departamentos/venta/partido-de-tandil"),
    ("departamento", "alquiler", "/departamentos/alquiler/partido-de-tandil"),
    ("casa",         "venta",    "/casas/venta/partido-de-tandil"),
    ("casa",         "alquiler", "/casas/alquiler/partido-de-tandil"),
    ("terreno",      "venta",    "/terrenos/venta/partido-de-tandil"),
    ("ph",           "venta",    "/ph/venta/partido-de-tandil"),
    ("local",        "alquiler", "/locales/alquiler/partido-de-tandil"),
]

MAX_PAGES_DEFAULT = 10    # páginas por combinación (~20 items/página)
DELAY_BETWEEN_REQUESTS = 2  # segundos entre requests


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


# ── Fetch HTML ────────────────────────────────────────────────────────────────

def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} para {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None


# ── Parsing ───────────────────────────────────────────────────────────────────

def _clean_text(s):
    """Decodifica entidades HTML y limpia espacios."""
    return re.sub(r'\s+', ' ', html_module.unescape(s)).strip()


def _extract_price_from_currency_and_amount(currency_str, amount_str):
    """Convierte strings de moneda/monto en floats."""
    amount_clean = re.sub(r'[^\d,\.]', '', amount_str)
    # ArgEnProp puede usar "." como separador de miles y "," como decimal
    # Normalmente es solo miles: "185.000" → 185000
    amount_clean = amount_clean.replace('.', '').replace(',', '')
    try:
        return float(amount_clean) if amount_clean else None
    except ValueError:
        return None


def parse_item(chunk, tipologia_default, operacion_default):
    """
    Convierte un bloque HTML de listing__item de ArgEnProp en un dict para Supabase.
    """

    # ── ID de la propiedad ──
    id_m = re.search(r'<div class="listing__item [^"]*" id="(\d+)"', chunk)
    if not id_m:
        return None
    fuente_id = id_m.group(1)

    # ── URL ──
    href_m = re.search(r'<a\s+href="(/[^"]+)"', chunk)
    url = BASE_URL + href_m.group(1) if href_m else None

    # ── Atributos del anchor (idmoneda, monto, dormitorios) ──
    anchor_m = re.search(r'<a\s[^>]*idaviso="\d+"[^>]*>', chunk, re.DOTALL)
    anchor_text = anchor_m.group(0) if anchor_m else chunk[:500]

    def _attr(name, text=anchor_text):
        m = re.search(rf'\b{name}="([^"]*)"', text)
        return m.group(1) if m else None

    idmoneda = _attr("idmoneda")          # "1"=ARS, "2"=USD
    monto_str = _attr("montonormalizado") # price value as string
    dorm_attr = _attr("dormitorios")

    # ── Precio desde anchor (más confiable que el HTML visible) ──
    precio_usd = None
    precio_ars = None
    if monto_str:
        try:
            monto = float(monto_str)
            if monto > 0:
                if idmoneda == "2":
                    precio_usd = monto
                elif idmoneda == "1":
                    precio_ars = monto
        except ValueError:
            pass

    # Fallback: precio desde el HTML visible si no obtuvimos del anchor
    if precio_usd is None and precio_ars is None:
        price_m = re.search(
            r'class="card__currency">([^<]+)</span>\s*([\d\.,]+)',
            chunk
        )
        if price_m:
            currency_symbol = price_m.group(1).strip()
            monto = _extract_price_from_currency_and_amount(currency_symbol, price_m.group(2))
            if monto and monto > 0:
                if "USD" in currency_symbol:
                    precio_usd = monto
                else:
                    precio_ars = monto

    # ── Dormitorios ──
    dormitorios = None
    if dorm_attr and dorm_attr.isdigit():
        dormitorios = int(dorm_attr)
    else:
        # Desde el listado de características
        dorm_feat = re.search(
            r'basico1-icon-cantidad_dormitorios[^<]*</i>\s*<span>\s*([\d]+)\s*dorm',
            chunk, re.IGNORECASE
        )
        if dorm_feat:
            try:
                dormitorios = int(dorm_feat.group(1))
            except ValueError:
                pass

    # ── Metros cuadrados ──
    metros_totales = None
    m2_m = re.search(
        r'basico1-icon-superficie_cubierta[^<]*</i>\s*<span>\s*([\d,\.]+)\s*m',
        chunk, re.IGNORECASE
    )
    if m2_m:
        try:
            metros_totales = float(m2_m.group(1).replace(',', '.'))
            if metros_totales == 0:
                metros_totales = None
        except ValueError:
            pass

    # ── Cochera ── (buscar en imagen alts y features, no en descripción libre)
    # ArgEnProp genera alts como "Departamento en Venta con 1 cocheras" para propiedades con cochera
    cochera = bool(re.search(
        r'<img\s[^>]*alt="[^"]*cochera[^"]*"',
        chunk, re.IGNORECASE
    )) or bool(re.search(
        r'basico1-icon-cochera',
        chunk, re.IGNORECASE
    )) or bool(re.search(
        r'class="card__title[^"]*">[^<]*cochera',
        chunk, re.IGNORECASE
    ))

    # ── Zona / dirección ──
    zona = "Tandil"
    addr_m = re.search(r'class="card__address"[^>]*>\s*([^<]+)', chunk)
    if addr_m:
        addr_text = _clean_text(addr_m.group(1))
        if addr_text:
            zona = addr_text

    # ── Título ──
    titulo = ""
    title_m = re.search(r'class="card__title--primary">\s*([^<]+)', chunk)
    if title_m:
        titulo = _clean_text(title_m.group(1))

    # Fallback título: alt de primera imagen
    if not titulo:
        img_alt = re.search(r'<img\s+alt="([^"]+)"', chunk)
        if img_alt:
            titulo = _clean_text(img_alt.group(1))

    # ── Imagen ──
    imagen_url = None
    # Primera imagen con src (cargada) o data-src (lazy)
    img_m = re.search(
        r'<img[^>]+(?:src|data-src)="(https://[^"]+argenprop[^"]+)"',
        chunk
    )
    if img_m:
        imagen_url = img_m.group(1)

    # ── Tipología / operación ──
    tipologia = tipologia_default
    operacion = operacion_default

    return {
        "fuente": "argenprop",
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


# ── Scraping ──────────────────────────────────────────────────────────────────

def scrape_search(tipologia_db, operacion, path_base, max_pages):
    """Scrapea todas las páginas de una búsqueda específica de ArgEnProp."""
    results = {}  # fuente_id → prop

    for page in range(1, max_pages + 1):
        if page == 1:
            url = BASE_URL + path_base
        else:
            url = BASE_URL + path_base + f"?pagina-{page}"

        print(f"  Página {page}: {url}")

        html = fetch_html(url)
        if not html:
            break

        # Encontrar todos los listing__items
        item_positions = [
            m.start()
            for m in re.finditer(
                r'<div class="listing__item [^"]*" id="\d+"', html
            )
        ]

        if not item_positions:
            print(f"  → Sin items en página {page}, fin.")
            break

        page_results = 0
        for i, start in enumerate(item_positions):
            end = item_positions[i + 1] if i + 1 < len(item_positions) else start + 8000
            chunk = html[start:end]

            prop = parse_item(chunk, tipologia_db, operacion)
            if prop and prop["fuente_id"] not in results:
                results[prop["fuente_id"]] = prop
                page_results += 1

        print(f"  → {page_results} propiedades nuevas ({len(results)} total)")

        # Verificar si hay página siguiente
        if f"pagina-{page + 1}" not in html:
            print(f"  → Sin página {page + 1}, fin.")
            break

        if page < max_pages:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    return results


def scrape_all(max_pages):
    """Scrapea todas las combinaciones configuradas."""
    all_props = {}

    for tipologia_db, operacion, path_base in SEARCH_CONFIGS:
        print(f"\n→ Scrapeando {tipologia_db}/{operacion}...")
        results = scrape_search(tipologia_db, operacion, path_base, max_pages)
        all_props.update(results)

    return list(all_props.values())


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
        print("Muestra (primeras 5):")
        for p in props[:5]:
            if p.get("precio_usd"):
                precio_str = f"USD {p['precio_usd']}"
            elif p.get("precio_ars"):
                precio_str = f"ARS {p['precio_ars']} → USD {p.get('precio_usd', '?')}"
            else:
                precio_str = "sin precio"
            m2_display = f"{p['metros_totales']}m²" if p.get('metros_totales') else "?m²"
            print(f"  ID={p['fuente_id']} | {p['tipologia']}/{p['operacion']} | "
                  f"{precio_str} | {p['zona'][:40]} | {m2_display} | "
                  f"{p.get('dormitorios','?')} dorm | cochera={p.get('cochera')}")
        return len(props), 0

    batch_size = 50
    inserted = 0
    errors = 0

    for i in range(0, len(props), batch_size):
        batch = props[i: i + batch_size]
        body = json.dumps(batch).encode("utf-8")
        req = urllib.request.Request(api_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                inserted += len(batch)
                print(f"  Lote {i // batch_size + 1}: {len(batch)} propiedades upsertadas ✓")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(f"  Error HTTP {e.code}: {error_body[:200]}", file=sys.stderr)
            errors += len(batch)
        except Exception as e:
            print(f"  Error lote {i // batch_size + 1}: {e}", file=sys.stderr)
            errors += len(batch)

    return inserted, errors


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper ArgEnProp → Supabase")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en Supabase")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT,
                        help=f"Páginas por búsqueda (default: {MAX_PAGES_DEFAULT})")
    args = parser.parse_args()

    print(f"=== Scraper ArgEnProp Inmuebles ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Max páginas por categoría: {args.max_pages}")

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en .env", file=sys.stderr)
        sys.exit(1)

    props = scrape_all(args.max_pages)
    print(f"\nTotal propiedades únicas scraped: {len(props)}")

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

    inserted, errors = upsert_supabase(props, supabase_url, service_key, dry_run=args.dry_run)

    print(f"\n=== Resultado ===")
    print(f"Upsertadas: {inserted}")
    print(f"Errores:    {errors}")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
