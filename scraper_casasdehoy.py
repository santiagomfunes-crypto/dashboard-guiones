#!/usr/bin/env python3
"""
Scraper diario CasasDeHoy → Supabase
Extrae propiedades en Tandil desde casasdehoy.com.ar
y hace upsert en la tabla propiedades_mercado.

Uso: python3 scraper_casasdehoy.py
     python3 scraper_casasdehoy.py --dry-run
     python3 scraper_casasdehoy.py --max-pages 3
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

BASE_URL = "https://www.casasdehoy.com.ar/2022/resultados.php"
PROP_BASE_URL = "https://www.casasdehoy.com.ar/2022/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-AR,es;q=0.9",
}

# Combinaciones a scrapear: (tipo_cdh, tipologia_db, operacion)
SEARCH_CONFIGS = [
    ("Casas",          "casa",          "venta"),
    ("Casas",          "casa",          "alquiler"),
    ("Departamentos",  "departamento",  "venta"),
    ("Departamentos",  "departamento",  "alquiler"),
    ("Lotes",          "terreno",       "venta"),
    ("Locales",        "local",         "alquiler"),
    ("PH",             "ph",            "venta"),
]

MAX_PAGES_DEFAULT = 5    # páginas por combinación (~24 items/página)
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


# ── Scraping ──────────────────────────────────────────────────────────────────

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


def parse_card(card_html, tipologia_default, operacion_default):
    """Convierte una card HTML de CasasDeHoy en un dict listo para Supabase."""

    # ── ID de la propiedad ──
    id_m = re.search(r'<div id="(\d+)" class="carousel', card_html)
    if not id_m:
        return None
    prop_id = id_m.group(1)

    # ── URL ──
    url_m = re.search(r'href="([^"]+\.html)"', card_html)
    relative_url = url_m.group(1) if url_m else None
    url = PROP_BASE_URL + relative_url if relative_url else None

    # ── Imagen (background-image del primer item del carousel) ──
    img_m = re.search(r'background-image:\s*url\([\'"]?\.\./(fotos_nuevas/[^\'")]+)[\'"]?\)', card_html)
    imagen_url = f"https://www.casasdehoy.com.ar/2022/{img_m.group(1)}" if img_m else None

    # ── Operación (venta/alquiler) ──
    if re.search(r'class="sale-tag\s+alquiler', card_html, re.IGNORECASE):
        operacion = "alquiler"
    elif re.search(r'class="sale-tag\s+venta', card_html, re.IGNORECASE):
        operacion = "venta"
    else:
        operacion = operacion_default

    # ── Título / Zona ──
    h2_m = re.search(r'<h2[^>]*>.*?<a[^>]*>(.*?)</a>', card_html, re.DOTALL)
    titulo = ""
    if h2_m:
        titulo = re.sub(r'<[^>]+>', '', h2_m.group(1)).strip()

    zona = titulo if titulo else "Tandil"

    # ── Tipología (del <p class="tipo">) ──
    tipo_m = re.search(r'<p class="tipo"[^>]*>(.*?)</p>', card_html, re.DOTALL)
    tipologia = tipologia_default
    if tipo_m:
        tipo_text = re.sub(r'<[^>]+>', '', tipo_m.group(1)).strip().lower()
        for t in ["departamento", "casa", "lote", "terreno", "local", "ph", "quinta", "campo", "galpón", "cochera"]:
            if t in tipo_text:
                tipologia = t
                break

    # ── Precio ──
    precio_usd = None
    precio_ars = None
    usd_m = re.search(r'<span[^>]*class="precio"[^>]*>\s*U\$S\s*([\d.]+)', card_html)
    if usd_m:
        try:
            precio_usd = int(usd_m.group(1).replace(".", ""))
        except ValueError:
            pass
    if precio_usd is None:
        ars_m = re.search(r'<span[^>]*class="precio"[^>]*>\s*\$\s*([\d.,]+)', card_html)
        if ars_m:
            try:
                precio_ars = int(ars_m.group(1).replace(".", "").replace(",", ""))
            except ValueError:
                pass

    # ── Atributos de la propiedad (comodidades) ──
    metros_totales = None
    dormitorios = None
    cochera = False

    # Metros cuadrados: icono fa-arrows-alt + "m²: XXX"
    m2_m = re.search(r'fa-arrows-alt[^>]*>.*?m²:\s*([\d.,]+)', card_html, re.DOTALL)
    if m2_m:
        try:
            metros_totales = float(m2_m.group(1).replace(",", "."))
            if metros_totales == 0:
                metros_totales = None  # 0 significa "no informado"
        except ValueError:
            pass

    # Dormitorios: icono fa-bed + número
    bed_m = re.search(r'fa-bed[^>]*>.*?</i>[^<]*\n?\s*(\d+)', card_html, re.DOTALL)
    if bed_m:
        try:
            dormitorios = int(bed_m.group(1).strip())
        except ValueError:
            pass

    # Cocheras: icono fa-car + número > 0
    car_m = re.search(r'fa-car[^>]*>.*?</i>[^<]*\n?\s*(\d+)', card_html, re.DOTALL)
    if car_m:
        try:
            cochera = int(car_m.group(1).strip()) > 0
        except ValueError:
            pass

    return {
        "fuente": "casasdehoy",
        "fuente_id": prop_id,
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


def scrape_search(tipo_cdh, tipologia_db, operacion, max_pages):
    """Scrapea todas las páginas de una búsqueda específica."""
    opcion_str = "Venta" if operacion == "venta" else "Alquiler"
    results = {}  # fuente_id → prop

    for page in range(1, max_pages + 1):
        url = (
            f"{BASE_URL}?pagina={page}&desde=1"
            f"&opcion={urllib.parse.quote(opcion_str)}"
            f"&tipo={urllib.parse.quote(tipo_cdh)}"
        )
        print(f"  Página {page}: {url}")

        html = fetch_html(url)
        if not html:
            break

        # Encontrar todas las cards
        card_starts = [m.start() for m in re.finditer(
            r'<div class="div-articulo propiedades clearfix">', html
        )]

        if not card_starts:
            print(f"  → Sin cards en página {page}, fin.")
            break

        page_results = 0
        for i, start in enumerate(card_starts):
            end = card_starts[i + 1] if i + 1 < len(card_starts) else start + 5000
            card_html = html[start:end]

            prop = parse_card(card_html, tipologia_db, operacion)
            if prop and prop["fuente_id"] not in results:
                results[prop["fuente_id"]] = prop
                page_results += 1

        print(f"  → {page_results} propiedades nuevas ({len(results)} total)")

        # Verificar si hay página siguiente
        if f"pagina={page + 1}" not in html:
            print(f"  → Sin página {page + 1}, fin.")
            break

        if page < max_pages:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    return results


def scrape_all(max_pages):
    """Scrapea todas las combinaciones configuradas."""
    # importar aquí para compatibilidad
    import urllib.parse

    all_props = {}  # fuente_id → prop

    for tipo_cdh, tipologia_db, operacion in SEARCH_CONFIGS:
        print(f"\n→ Scrapeando {tipo_cdh}/{operacion}...")
        results = scrape_search(tipo_cdh, tipologia_db, operacion, max_pages)
        all_props.update(results)

    return list(all_props.values())


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
    """Retorna dict {fuente_id: {id, precio_usd}} para propiedades ya existentes en DB."""
    if not fuente_ids:
        return {}

    result = {}
    batch_size = 100
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
    }

    for i in range(0, len(fuente_ids), batch_size):
        batch = fuente_ids[i: i + batch_size]
        ids_str = ",".join(str(fid) for fid in batch)
        url = (
            f"{supabase_url}/rest/v1/propiedades_mercado"
            f"?select=id,fuente_id,precio_usd"
            f"&fuente=eq.casasdehoy"
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
    """Registra cambios de precio en propiedades_precio_historial."""
    historial_rows = []
    hoy = date.today().isoformat()

    for p in props:
        fid = str(p.get("fuente_id"))
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
            "fuente": "casasdehoy",
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
        print("Muestra (primeras 5):")
        for p in props[:5]:
            if p.get("precio_usd"):
                precio_str = f"USD {p['precio_usd']}"
            elif p.get("precio_ars"):
                precio_str = f"ARS {p['precio_ars']} → USD {p.get('precio_usd', '?')}"
            else:
                precio_str = "sin precio"
            print(f"  ID={p['fuente_id']} | {p['tipologia']}/{p['operacion']} | "
                  f"{precio_str} | {p['zona'][:40]}")
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


def report_to_supabase(supabase_url, service_key, inserted, errors, dry_run):
    """Guarda un reporte del scraping en la tabla reportes."""
    if dry_run:
        return

    report = {
        "tipo": "scraping",
        "fuente": "casasdehoy",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "resultado": {
            "insertadas": inserted,
            "errores": errors,
            "estado": "ok" if errors == 0 else "parcial"
        }
    }

    api_url = f"{supabase_url}/rest/v1/reportes"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    # Buscar el schema de la tabla reportes primero
    try:
        req = urllib.request.Request(
            f"{api_url}?limit=1",
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            sample = json.loads(resp.read())
    except Exception:
        sample = []

    if sample:
        # Adaptar al schema existente
        cols = list(sample[0].keys()) if sample else []
        print(f"  Schema reportes: {cols}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import urllib.parse

    parser = argparse.ArgumentParser(description="Scraper CasasDeHoy Inmuebles → Supabase")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en Supabase")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT,
                        help=f"Páginas por búsqueda (default: {MAX_PAGES_DEFAULT})")
    args = parser.parse_args()

    print(f"=== Scraper CasasDeHoy Inmuebles ===")
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

    # Enriquecer con zona_normalizada
    enrich_with_zona(props)

    # Leer precios existentes antes del upsert (para detectar cambios)
    existing_prices = {}
    if not args.dry_run:
        print("Leyendo precios existentes para historial...")
        fuente_ids = [str(p["fuente_id"]) for p in props]
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
