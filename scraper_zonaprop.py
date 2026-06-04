#!/usr/bin/env python3
"""
Scraper diario ZonaProp → Supabase
Extrae propiedades en Tandil desde zonaprop.com.ar con Playwright (renderiza JS)
y hace upsert en la tabla propiedades_mercado.

Uso: python3 scraper_zonaprop.py
     python3 scraper_zonaprop.py --dry-run
     python3 scraper_zonaprop.py --max-pages 3
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

# URLs a scrapear: (tipologia, operacion, url_base)
# Paginación ZonaProp: base.html → base-pagina-2.html → base-pagina-3.html
SEARCH_URLS = [
    ("departamento", "venta",    "https://www.zonaprop.com.ar/departamentos-venta-tandil.html"),
    ("departamento", "alquiler", "https://www.zonaprop.com.ar/departamentos-alquiler-tandil.html"),
    ("casa",         "venta",    "https://www.zonaprop.com.ar/casas-venta-tandil.html"),
    ("casa",         "alquiler", "https://www.zonaprop.com.ar/casas-alquiler-tandil.html"),
    ("terreno",      "venta",    "https://www.zonaprop.com.ar/terrenos-venta-tandil.html"),
    ("ph",           "venta",    "https://www.zonaprop.com.ar/ph-venta-tandil.html"),
    ("local",        "alquiler", "https://www.zonaprop.com.ar/locales-comerciales-alquiler-tandil.html"),
]

MAX_PAGES_DEFAULT = 5     # máximo de páginas por combinación (~20 items/página)
DELAY_BETWEEN_REQUESTS = 4  # segundos entre requests
PAGE_LOAD_TIMEOUT = 30000   # ms
PAGE_JS_WAIT = 9            # segundos de espera para JS (necesario para Cloudflare)
DELAY_BETWEEN_PAGES = 5     # segundos entre páginas (rotación de contexto)


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


# ── URL de paginación ──────────────────────────────────────────────────────────

def get_page_url(base_url, page_num):
    """Construye la URL paginada de ZonaProp."""
    if page_num == 1:
        return base_url
    # Insertar -pagina-N antes de .html
    return re.sub(r'\.html$', f'-pagina-{page_num}.html', base_url)


# ── Extracción desde __NEXT_DATA__ ────────────────────────────────────────────

def extract_next_data(html):
    """Extrae el JSON de __NEXT_DATA__ embebido en el HTML de ZonaProp."""
    m = re.search(
        r'<script\s+id="__NEXT_DATA__"\s+type="application/json"\s*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def get_postings_from_next_data(next_data):
    """
    Navega el árbol de __NEXT_DATA__ para encontrar la lista de postings.
    ZonaProp puede tenerlos en distintas rutas según la versión.
    Retorna (lista_de_postings, total_paginas) o ([], None).
    """
    try:
        page_props = next_data["props"]["pageProps"]
    except (KeyError, TypeError):
        return [], None

    # Intento 1: listPostings directo
    postings = page_props.get("listPostings") or []
    if postings:
        pagination = page_props.get("paginacion") or {}
        total_pages = pagination.get("cantidadPaginas")
        return postings, total_pages

    # Intento 2: dentro de algún wrapper de datos
    for key in ("searchResult", "results", "data"):
        wrapper = page_props.get(key) or {}
        if isinstance(wrapper, dict):
            postings = wrapper.get("listPostings") or wrapper.get("postings") or []
            if postings:
                pagination = wrapper.get("paginacion") or {}
                total_pages = pagination.get("cantidadPaginas")
                return postings, total_pages

    return [], None


def parse_posting(posting, tipologia_default, operacion_default):
    """
    Convierte un posting de ZonaProp en un dict listo para Supabase.
    Maneja distintas variantes del schema que ZonaProp puede usar.
    """
    # ── ID ──
    fuente_id = (
        str(posting.get("postingId") or "")
        or str(posting.get("id") or "")
    )
    if not fuente_id:
        return None

    # ── URL ──
    raw_url = posting.get("url") or posting.get("link") or ""
    if raw_url and not raw_url.startswith("http"):
        url = f"https://www.zonaprop.com.ar{raw_url}"
    else:
        url = raw_url

    # ── Título ──
    titulo = (
        posting.get("title")
        or posting.get("titulo")
        or posting.get("description")
        or ""
    )
    if isinstance(titulo, dict):
        titulo = titulo.get("text") or titulo.get("value") or ""

    # ── Operación y tipología ──
    operacion = operacion_default
    tipologia = tipologia_default

    # Intentar inferir desde el título o campos explícitos
    tipo_raw = (posting.get("type") or posting.get("tipo") or "").lower()
    op_raw = (posting.get("operation") or posting.get("operacion") or "").lower()

    if "alquiler" in op_raw or "rent" in op_raw:
        operacion = "alquiler"
    elif "venta" in op_raw or "sale" in op_raw:
        operacion = "venta"

    for t in ["departamento", "casa", "ph", "terreno", "lote", "local", "oficina", "cochera", "campo"]:
        if t in tipo_raw:
            tipologia = t
            break

    # ── Precio ──
    precio_usd = None
    precio_ars = None

    # Variante A: priceDetails (lista)
    price_details = posting.get("priceDetails") or []
    if isinstance(price_details, list):
        for pd in price_details:
            currency = (pd.get("currency") or "").upper()
            amount = pd.get("amount")
            if amount is None:
                # intentar parsear formattedAmount
                formatted = pd.get("formattedAmount") or ""
                m = re.search(r'[\d.,]+', formatted.replace(".", "").replace(",", ""))
                if m:
                    try:
                        amount = float(m.group(0))
                    except ValueError:
                        pass
            if currency == "USD" and amount:
                precio_usd = float(amount)
                break
            elif currency in ("ARS", "PESOS", "$") and amount:
                precio_ars = float(amount)
                break

    # Variante B: price dict
    if precio_usd is None and precio_ars is None:
        price_obj = posting.get("price") or posting.get("precio") or {}
        if isinstance(price_obj, dict):
            currency = (price_obj.get("currency") or price_obj.get("moneda") or "").upper()
            amount = price_obj.get("amount") or price_obj.get("valor")
            if amount:
                if currency == "USD":
                    precio_usd = float(amount)
                elif currency in ("ARS", "PESOS"):
                    precio_ars = float(amount)

    # Variante C: campos planos
    if precio_usd is None and precio_ars is None:
        if posting.get("priceUSD"):
            precio_usd = float(posting["priceUSD"])
        elif posting.get("priceARS"):
            precio_ars = float(posting["priceARS"])

    # ── Atributos ──
    dormitorios = None
    metros_totales = None
    cochera = False

    # Variante A: dict "attributes"
    attrs = posting.get("attributes") or posting.get("atributos") or {}
    if isinstance(attrs, dict):
        dormitorios = attrs.get("dormitorios") or attrs.get("bedrooms")
        ambientes = attrs.get("ambientes") or attrs.get("rooms")
        if dormitorios is None and ambientes:
            dormitorios = max(0, int(ambientes) - 1)
        metros_totales = (
            attrs.get("superficieCubierta")
            or attrs.get("superficie")
            or attrs.get("totalArea")
            or attrs.get("coveredArea")
        )
        cocheras_val = attrs.get("cocheras") or attrs.get("parkings") or 0
        cochera = int(cocheras_val) > 0 if cocheras_val else False

    # Variante B: lista de features/atributos
    if dormitorios is None and metros_totales is None:
        features = (
            posting.get("features")
            or posting.get("characteristics")
            or posting.get("generalFeatures")
            or []
        )
        if isinstance(features, list):
            for feat in features:
                if not isinstance(feat, dict):
                    continue
                label = (feat.get("label") or feat.get("name") or feat.get("key") or "").lower()
                value = feat.get("value") or feat.get("amount") or ""
                if "dormitorio" in label or "bedroom" in label:
                    try:
                        dormitorios = int(value)
                    except (ValueError, TypeError):
                        pass
                elif "ambiente" in label or "room" in label:
                    try:
                        ambientes = int(value)
                        if dormitorios is None:
                            dormitorios = max(0, ambientes - 1)
                    except (ValueError, TypeError):
                        pass
                elif "m²" in label or "superficie" in label or "area" in label or "metros" in label:
                    try:
                        metros_totales = float(str(value).replace(",", "."))
                    except (ValueError, TypeError):
                        pass
                elif "cochera" in label or "parking" in label or "garage" in label:
                    try:
                        cochera = int(value) > 0
                    except (ValueError, TypeError):
                        cochera = bool(value)

    # Conversiones de tipo
    if dormitorios is not None:
        try:
            dormitorios = int(dormitorios)
        except (ValueError, TypeError):
            dormitorios = None
    if metros_totales is not None:
        try:
            metros_totales = float(metros_totales)
            if metros_totales == 0:
                metros_totales = None
        except (ValueError, TypeError):
            metros_totales = None

    # ── Zona ──
    zona = "Tandil"
    location = (
        posting.get("postingLocation")
        or posting.get("location")
        or posting.get("ubicacion")
        or {}
    )
    if isinstance(location, dict):
        loc_inner = location.get("location") or location.get("barrio") or location
        if isinstance(loc_inner, dict):
            zona = loc_inner.get("name") or loc_inner.get("nombre") or "Tandil"
        elif isinstance(loc_inner, str):
            zona = loc_inner

    # ── Imagen ──
    imagen_url = None
    main_pic = posting.get("mainPicture") or posting.get("mainPhoto") or posting.get("thumbnail") or {}
    if isinstance(main_pic, dict):
        imagen_url = (
            main_pic.get("thumb870x470")
            or main_pic.get("url")
            or main_pic.get("src")
            or main_pic.get("thumb")
        )
    elif isinstance(main_pic, str):
        imagen_url = main_pic

    if not imagen_url:
        photos = posting.get("photos") or posting.get("fotos") or []
        if isinstance(photos, list) and photos:
            first = photos[0]
            if isinstance(first, dict):
                imagen_url = (
                    first.get("thumb870x470")
                    or first.get("url")
                    or first.get("src")
                )
            elif isinstance(first, str):
                imagen_url = first

    return {
        "fuente": "zonaprop",
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
        "titulo": titulo[:500] if titulo else "",
        "imagen_url": imagen_url,
    }


# ── Extracción de respaldo desde HTML ─────────────────────────────────────────

def extract_from_json_scripts(html, tipologia, operacion):
    """
    Respaldo: busca datos en otros scripts JSON del HTML de ZonaProp
    cuando __NEXT_DATA__ no tiene postings.
    """
    props = {}

    # Buscar bloques JSON con "postingId"
    for block_match in re.finditer(r'\{[^{}]*"postingId"\s*:\s*\d+[^{}]*\}', html):
        try:
            obj = json.loads(block_match.group(0))
            prop = parse_posting(obj, tipologia, operacion)
            if prop:
                props[prop["fuente_id"]] = prop
        except json.JSONDecodeError:
            pass

    # Buscar IDs de propiedades en URLs del HTML
    if not props:
        for m in re.finditer(r'href="(/propiedades/[^"]*?-(\d{8,})\.html)"', html):
            url_path = m.group(1)
            fuente_id = m.group(2)
            if fuente_id not in props:
                props[fuente_id] = {
                    "fuente": "zonaprop",
                    "fuente_id": fuente_id,
                    "url": f"https://www.zonaprop.com.ar{url_path}",
                    "tipologia": tipologia,
                    "operacion": operacion,
                    "zona": "Tandil",
                    "precio_usd": None,
                    "precio_ars": None,
                    "tipo_cambio_usd": None,
                    "dormitorios": None,
                    "metros_totales": None,
                    "cochera": False,
                    "titulo": "",
                    "imagen_url": None,
                }

    return list(props.values())


# ── Extracción DOM (nuevo rendering SSR de ZonaProp, jun-2026) ────────────────

_DOM_EXTRACT_JS = """() => {
    const cards = document.querySelectorAll('[data-id][data-to-posting]');
    const results = [];
    for (const card of cards) {
        const id = card.getAttribute('data-id');
        const urlPath = card.getAttribute('data-to-posting') || '';

        // Imagen y título desde primer img con alt
        const img = card.querySelector('img[alt]');
        const titulo = img ? img.getAttribute('alt') : '';
        const imagenUrl = img ? img.getAttribute('src') : '';

        // Precio: buscar elemento con data-qa o clase price
        let precio = '';
        const priceSelectors = [
            '[data-qa="POSTING_CARD_PRICE"]',
            '[class*="price"]',
            '[class*="Price"]',
        ];
        for (const sel of priceSelectors) {
            const el = card.querySelector(sel);
            if (el && el.textContent.trim()) {
                precio = el.textContent.trim();
                break;
            }
        }

        // Features: m², ambientes, dormitorios
        const features = [];
        const featSelectors = [
            '[data-qa="POSTING_CARD_FEATURES"] span',
            '[class*="cardFeatures"] li',
            '[class*="feature"] span',
        ];
        for (const sel of featSelectors) {
            card.querySelectorAll(sel).forEach(el => {
                const t = el.textContent.trim();
                if (t) features.push(t);
            });
            if (features.length > 0) break;
        }

        // Zona/dirección
        let zona = '';
        const locSelectors = [
            '[data-qa="POSTING_CARD_LOCATION"]',
            '[class*="location"]',
            '[class*="Location"]',
        ];
        for (const sel of locSelectors) {
            const el = card.querySelector(sel);
            if (el && el.textContent.trim()) {
                zona = el.textContent.trim();
                break;
            }
        }

        results.push({id, urlPath, titulo, precio, features, zona, imagenUrl});
    }
    return results;
}"""


def parse_dom_prop(raw, tipologia_default, operacion_default):
    """
    Convierte un posting extraído del DOM (nuevo rendering SSR de ZonaProp)
    en un dict listo para Supabase.
    """
    fuente_id = str(raw.get("id") or "").strip()
    if not fuente_id:
        return None

    # URL: limpiar parámetros de tracking
    url_path = (raw.get("urlPath") or "").split("?")[0]
    url = f"https://www.zonaprop.com.ar{url_path}" if url_path else ""

    titulo = (raw.get("titulo") or "")[:500]

    # ── Precio ──
    precio_usd = None
    precio_ars = None
    precio_text = raw.get("precio") or ""

    usd_m = re.search(r'USD\s*([\d\.]+)', precio_text)
    if usd_m:
        try:
            precio_usd = float(usd_m.group(1).replace(".", ""))
        except ValueError:
            pass

    if precio_usd is None:
        ars_m = re.search(r'\$\s*([\d\.]+)', precio_text)
        if ars_m:
            try:
                precio_ars = float(ars_m.group(1).replace(".", ""))
            except ValueError:
                pass

    # ── Features ──
    dormitorios = None
    metros_totales = None
    cochera = False

    for feat in (raw.get("features") or []):
        feat_l = feat.lower()
        m2 = re.search(r'([\d,\.]+)\s*m²', feat_l)
        if m2:
            try:
                metros_totales = float(m2.group(1).replace(",", "."))
            except ValueError:
                pass
        dorm = re.search(r'(\d+)\s*dorm', feat_l)
        if dorm:
            dormitorios = int(dorm.group(1))
        elif dormitorios is None:
            amb = re.search(r'(\d+)\s*amb', feat_l)
            if amb:
                dormitorios = max(0, int(amb.group(1)) - 1)
        if "coch" in feat_l or "garage" in feat_l or "parking" in feat_l:
            cochera = True

    if metros_totales == 0:
        metros_totales = None

    # ── Zona ──
    zona_raw = (raw.get("zona") or "Tandil")
    zona = zona_raw.split(",")[0].strip() or "Tandil"

    # ── Imagen ──
    imagen_url = raw.get("imagenUrl") or None

    return {
        "fuente": "zonaprop",
        "fuente_id": fuente_id,
        "url": url,
        "tipologia": tipologia_default,
        "operacion": operacion_default,
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


# ── Scraping con Playwright ────────────────────────────────────────────────────

def _make_context(browser):
    """Crea un nuevo contexto Playwright fresco (necesario para evadir Cloudflare)."""
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="es-AR",
        timezone_id="America/Argentina/Buenos_Aires",
        viewport={"width": 1280, "height": 900},
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return context


def fetch_page_playwright(browser, url):
    """
    Carga una URL con un contexto Playwright FRESCO y retorna (html, dom_props_raw).
    ZonaProp (Cloudflare) bloquea después de la primera carga del mismo contexto,
    por lo que se necesita un contexto nuevo por página.
    """
    context = _make_context(browser)
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        time.sleep(PAGE_JS_WAIT)
        html = page.content()
        # Extracción DOM directa (nuevo rendering SSR, jun-2026)
        try:
            dom_raw = page.evaluate(_DOM_EXTRACT_JS)
        except Exception:
            dom_raw = []
        return html, dom_raw
    except Exception as e:
        print(f"  Error Playwright en {url}: {e}", file=sys.stderr)
        return None, []
    finally:
        context.close()


def scrape_all(max_pages):
    """
    Scrapea todas las URLs configuradas y retorna lista de propiedades.
    Usa un contexto Playwright fresco por página para evadir Cloudflare.
    """
    from playwright.sync_api import sync_playwright

    all_props = {}  # fuente_id → prop (dedup global)

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

        for tipologia, operacion, base_url in SEARCH_URLS:
            print(f"\n→ Scrapeando {tipologia}/{operacion}...")

            for pg_idx in range(1, max_pages + 1):
                url = get_page_url(base_url, pg_idx)
                print(f"  Página {pg_idx}: {url}")

                html, dom_raw = fetch_page_playwright(browser, url)
                if not html:
                    break

                props_this_page = []

                # Prioridad 1: extracción DOM (nuevo SSR, jun-2026)
                if dom_raw:
                    print(f"  → {len(dom_raw)} cards en DOM")
                    for raw in dom_raw:
                        prop = parse_dom_prop(raw, tipologia, operacion)
                        if prop:
                            props_this_page.append(prop)

                # Prioridad 2: __NEXT_DATA__ (rendering anterior Next.js)
                if not props_this_page:
                    next_data = extract_next_data(html)
                    if next_data:
                        postings, total_pages_nd = get_postings_from_next_data(next_data)
                        if postings:
                            print(f"  → {len(postings)} postings en __NEXT_DATA__")
                            for posting in postings:
                                prop = parse_posting(posting, tipologia, operacion)
                                if prop:
                                    props_this_page.append(prop)

                # Prioridad 3: extracción regex de respaldo
                if not props_this_page:
                    fallback_props = extract_from_json_scripts(html, tipologia, operacion)
                    if fallback_props:
                        print(f"  → {len(fallback_props)} propiedades por extracción de respaldo")
                        props_this_page = fallback_props

                if not props_this_page:
                    print(f"  → Sin resultados en página {pg_idx}, cortando paginación")
                    break

                new_count = 0
                for prop in props_this_page:
                    if prop["fuente_id"] not in all_props:
                        all_props[prop["fuente_id"]] = prop
                        new_count += 1
                print(f"  → {new_count} nuevas (total global: {len(all_props)})")

                # Cortar paginación si la página estaba incompleta (<20 cards = última)
                if len(props_this_page) < 20:
                    print(f"  → Página incompleta ({len(props_this_page)} props), fin.")
                    break

                # Verificar presencia de siguiente página en el HTML
                next_page_slug = f"-pagina-{pg_idx + 1}.html"
                if next_page_slug not in html:
                    print(f"  → No se detectó página {pg_idx + 1}, fin.")
                    break

                if pg_idx < max_pages:
                    time.sleep(DELAY_BETWEEN_PAGES)

        browser.close()

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
                precio_str = f"USD {p['precio_usd']:,.0f}"
            elif p.get("precio_ars"):
                precio_str = f"ARS {p['precio_ars']:,.0f}"
            else:
                precio_str = "sin precio"
            print(f"  ID={p['fuente_id']} | {p['tipologia']}/{p['operacion']} | "
                  f"{precio_str} | {str(p['zona'])[:30]}")
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
            print(f"  Error HTTP {e.code} en lote {i // batch_size + 1}: {error_body[:300]}", file=sys.stderr)
            errors += len(batch)
        except Exception as e:
            print(f"  Error en lote {i // batch_size + 1}: {e}", file=sys.stderr)
            errors += len(batch)

    return inserted, errors


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper ZonaProp Inmuebles → Supabase")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en Supabase")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT,
                        help=f"Páginas por búsqueda (default: {MAX_PAGES_DEFAULT})")
    args = parser.parse_args()

    print(f"=== Scraper ZonaProp Inmuebles (Playwright) ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Max páginas por categoría: {args.max_pages}")

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en .env", file=sys.stderr)
        sys.exit(1)

    props = scrape_all(args.max_pages)
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

    inserted, errors = upsert_supabase(props, supabase_url, service_key, dry_run=args.dry_run)

    print(f"\n=== Resultado ===")
    print(f"Upsertadas: {inserted}")
    print(f"Errores:    {errors}")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
