#!/usr/bin/env python3
"""
Servidor HTTP on-demand para fichas de propiedades.
Endpoint: GET /property?url=<url-de-propiedad>
Portales soportados: CasasDeHoy, MercadoLibre, Zonaprop, Argenprop
"""

import os
import re
import json
import urllib.request
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

PORT = int(os.environ.get("PORT", 8080))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "https://santiagomfunes-crypto.github.io")

HEADERS = {
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


# ── Detectar portal ────────────────────────────────────────────────────────────

def detect_portal(url: str) -> str:
    if "mercadolibre.com.ar" in url:
        return "mercadolibre"
    if "casasdehoy.com.ar" in url:
        return "casasdehoy"
    if "zonaprop.com.ar" in url:
        return "zonaprop"
    if "argenprop.com" in url:
        return "argenprop"
    return "unknown"


# ── Helpers ────────────────────────────────────────────────────────────────────

def fetch_html(url: str, referer: Optional[str] = None) -> Optional[str]:
    hdrs = dict(HEADERS)
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
    if "departamento" in r or "depto" in r:
        return "departamento"
    if "ph" in r:
        return "PH"
    if "local" in r or "comercial" in r:
        return "local"
    if "terreno" in r or "lote" in r:
        return "terreno"
    if "oficina" in r:
        return "oficina"
    if "casa" in r or "chalet" in r:
        return "casa"
    return raw.strip()


def clean_result(data: dict) -> dict:
    return {k: v for k, v in data.items()
            if v is not None and v != "" and not (isinstance(v, list) and len(v) == 0)}


# ── Parser: CasasDeHoy ─────────────────────────────────────────────────────────

def parse_casasdehoy(html: str) -> dict:
    result = {}

    # Tipo y barrio desde <title>
    title_text = first_match(r"<title>([\s\S]*?)</title>", html, re.IGNORECASE)
    if title_text:
        clean = strip_html(title_text).strip()
        result["tipo"] = normalize_tipo(clean)
        parts = clean.split(" - ")
        if len(parts) >= 2:
            result["barrio"] = parts[1].strip()[:100]

    # Precio USD: <h3 class="azul">...<strong>U$S 580.000</strong></h3>
    precio_usd_raw = first_match(
        r'<h3[^>]*class="[^"]*azul[^"]*"[^>]*>[\s\S]*?U\$S\s*([\d.]+)', html, re.IGNORECASE
    )
    precio_ars_raw = first_match(
        r'<h3[^>]*class="[^"]*azul[^"]*"[^>]*>[\s\S]*?\$\s*([\d.]+)', html, re.IGNORECASE
    ) if not precio_usd_raw else None

    if precio_usd_raw:
        result["precio"] = int(precio_usd_raw.replace(".", "")) if precio_usd_raw else None
        result["moneda"] = "USD"
    elif precio_ars_raw:
        result["precio"] = int(precio_ars_raw.replace(".", "")) if precio_ars_raw else None
        result["moneda"] = "ARS"

    # m² total
    m2 = (
        first_match(r"fa-arrows[^>]*>[\s\S]{0,200}?([\d.,]+)\s*m(?:²|&sup2;)", html, re.IGNORECASE)
        or first_match(r"([\d.,]+)\s*m(?:²|&sup2;)", html, re.IGNORECASE)
    )
    if m2:
        result["sup_total"] = parse_num(m2)

    # m² cubierto
    m2_cub = first_match(r"([\d.,]+)\s*m(?:²|&sup2;)\s*(?:cub|cubierto)", html, re.IGNORECASE)
    if m2_cub:
        result["sup_cubierta"] = parse_num(m2_cub)

    # Dormitorios
    dorms = first_match(r"[Dd]ormitorios?:\s*(\d+)", html)
    if dorms:
        result["dormitorios"] = int(dorms)

    # Ambientes
    amb = first_match(r"[Aa]mbientes?:\s*(\d+)", html) or first_match(r"(\d+)\s*ambiente", html, re.IGNORECASE)
    if amb:
        result["ambientes"] = int(amb)

    # Baños
    banos = first_match(r"[Bb]a[ñn]os?:\s*(\d+)", html)
    if banos:
        result["banos"] = int(banos)

    # Descripción
    desc = first_match(
        r"Caracter[ií]sticas[\s\S]*?separator-line-gris[\s\S]*?<p[^>]*>([\s\S]*?)</p>",
        html, re.IGNORECASE
    )
    if desc:
        clean_desc = strip_html(desc).strip()
        if clean_desc and len(clean_desc) > 5:
            result["descripcion"] = clean_desc[:500]

    # Imágenes
    imagenes = []
    seen = set()
    for m in re.finditer(r"fotos_nuevas/[^\s\"'<>]+", html):
        img_url = f"https://www.casasdehoy.com.ar/{m.group(0)}"
        if img_url not in seen:
            seen.add(img_url)
            imagenes.append(img_url)
    if imagenes:
        result["imagenes"] = imagenes[:20]

    return result


# ── Parser: MercadoLibre API pública ──────────────────────────────────────────

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
        if attr_id == "BEDROOMS" and val:
            result["dormitorios"] = int(val) if val.isdigit() else None
        elif attr_id == "ROOMS" and val:
            result["ambientes"] = int(val) if val.isdigit() else None
        elif attr_id == "BATHROOMS" and val:
            result["banos"] = int(val) if val.isdigit() else None
        elif attr_id == "COVERED_AREA":
            result["sup_cubierta"] = parse_num(val)
        elif attr_id == "TOTAL_AREA":
            result["sup_total"] = parse_num(val)
        elif attr_id == "PROPERTY_TYPE" and val:
            result["tipo"] = normalize_tipo(val)
        elif attr_id == "NEIGHBORHOOD" and val:
            result["barrio"] = val

    loc = item.get("location", {})
    if loc and not result.get("barrio"):
        result["barrio"] = str(
            loc.get("neighborhood", {}).get("name", "") or
            loc.get("city", {}).get("name", "")
        ) or None

    return result


# ── Parser: MercadoLibre HTML (fallback) ─────────────────────────────────────

def parse_mercadolibre_html(html: str) -> dict:
    result = {}

    # Precio
    precio_usd = first_match(r"USD\s*([\d.,]+)", html, re.IGNORECASE)
    precio_ars = first_match(r"\$\s*([\d.]+)", html)
    if precio_usd:
        result["precio"] = parse_num(precio_usd)
        result["moneda"] = "USD"
    elif precio_ars:
        result["precio"] = parse_num(precio_ars)
        result["moneda"] = "ARS"

    # Tipo
    tipo_h1 = first_match(r'<h1[^>]*class="[^"]*ui-pdp-title[^"]*"[^>]*>(.*?)</h1>', html, re.IGNORECASE)
    if tipo_h1:
        result["tipo"] = normalize_tipo(strip_html(tipo_h1))
        if not result.get("descripcion"):
            result["descripcion"] = strip_html(tipo_h1)

    # Barrio
    barrio = (
        first_match(r'class="[^"]*map__link[^"]*"[^>]*>(.*?)</a>', html, re.IGNORECASE)
        or first_match(r'"neighborhood"\s*:\s*"([^"]+)"', html, re.IGNORECASE)
    )
    if barrio:
        result["barrio"] = strip_html(barrio)

    # Atributos
    if not result.get("ambientes"):
        m = first_match(r"(\d+)\s*ambiente", html, re.IGNORECASE)
        if m:
            result["ambientes"] = int(m)
    if not result.get("dormitorios"):
        m = first_match(r"(\d+)\s*dormitorio", html, re.IGNORECASE)
        if m:
            result["dormitorios"] = int(m)
    if not result.get("banos"):
        m = first_match(r"(\d+)\s*ba[ñn]o", html, re.IGNORECASE)
        if m:
            result["banos"] = int(m)
    if not result.get("sup_cubierta"):
        m = first_match(r"([\d.,]+)\s*m[²2]\s*cub", html, re.IGNORECASE)
        if m:
            result["sup_cubierta"] = parse_num(m)
    if not result.get("sup_total"):
        m = first_match(r"([\d.,]+)\s*m[²2]\s*tot", html, re.IGNORECASE) or first_match(r"([\d.,]+)\s*m²", html)
        if m:
            result["sup_total"] = parse_num(m)

    return result


# ── Parser: Zonaprop ──────────────────────────────────────────────────────────

def find_in_object(obj, key, depth=0):
    if depth > 8 or not obj or not isinstance(obj, (dict, list)):
        return None
    if isinstance(obj, list):
        for item in obj:
            found = find_in_object(item, key, depth + 1)
            if found is not None:
                return found
        return None
    if key in obj:
        return obj[key]
    for v in obj.values():
        found = find_in_object(v, key, depth + 1)
        if found is not None:
            return found
    return None


def parse_zonaprop(html: str) -> dict:
    result = {}

    # JSON-LD
    for block in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE):
        try:
            data = json.loads(block)
            if data.get("description"):
                result["descripcion"] = data["description"][:500]
            if data.get("name"):
                result["tipo"] = normalize_tipo(data["name"])
            if data.get("numberOfRooms"):
                result["ambientes"] = int(data["numberOfRooms"])
            if data.get("numberOfBedrooms"):
                result["dormitorios"] = int(data["numberOfBedrooms"])
            if data.get("numberOfBathroomsTotal"):
                result["banos"] = int(data["numberOfBathroomsTotal"])
            if data.get("floorSize", {}).get("value"):
                result["sup_cubierta"] = parse_num(str(data["floorSize"]["value"]))
            if data.get("address", {}).get("addressLocality"):
                result["barrio"] = data["address"]["addressLocality"]
            offers = data.get("offers")
            if offers:
                if isinstance(offers, list):
                    offers = offers[0]
                if offers.get("price"):
                    result["precio"] = parse_num(str(offers["price"]))
                    result["moneda"] = "USD" if offers.get("priceCurrency") == "USD" else "ARS"
        except Exception:
            pass

    # __NEXT_DATA__
    nd_match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
    if nd_match:
        try:
            nd = json.loads(nd_match.group(1))
            listing = find_in_object(nd, "listing")
            if listing:
                attrs = find_in_object(listing, "attributes")
                if isinstance(attrs, list):
                    for a in attrs:
                        aid = str(a.get("id", "")).lower()
                        val = str(a.get("value", ""))
                        if aid == "total_area":
                            result["sup_total"] = parse_num(val)
                        elif aid == "covered_area":
                            result["sup_cubierta"] = parse_num(val)
                        elif aid == "rooms":
                            result["ambientes"] = int(val) if val.isdigit() else None
                        elif aid == "bedrooms":
                            result["dormitorios"] = int(val) if val.isdigit() else None
                        elif aid == "bathrooms":
                            result["banos"] = int(val) if val.isdigit() else None
        except Exception:
            pass

    # Fallback regex
    if not result.get("precio"):
        pu = first_match(r"USD\s*([\d.,]+)", html, re.IGNORECASE)
        pa = first_match(r"\$\s*([\d.]+)", html)
        if pu:
            result["precio"] = parse_num(pu)
            result["moneda"] = "USD"
        elif pa:
            result["precio"] = parse_num(pa)
            result["moneda"] = "ARS"
    if not result.get("ambientes"):
        m = first_match(r"(\d+)\s*ambiente", html, re.IGNORECASE)
        if m:
            result["ambientes"] = int(m)
    if not result.get("dormitorios"):
        m = first_match(r"(\d+)\s*dormitorio", html, re.IGNORECASE)
        if m:
            result["dormitorios"] = int(m)
    if not result.get("banos"):
        m = first_match(r"(\d+)\s*ba[ñn]o", html, re.IGNORECASE)
        if m:
            result["banos"] = int(m)

    return result


# ── Parser: Argenprop ─────────────────────────────────────────────────────────

def parse_argenprop(html: str) -> dict:
    result = {}

    nd_match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
    if nd_match:
        try:
            nd = json.loads(nd_match.group(1))
            listing = find_in_object(nd, "data") or find_in_object(nd, "property")
            if listing:
                tipo = str(find_in_object(listing, "propertyType") or find_in_object(listing, "type") or "")
                if tipo:
                    result["tipo"] = normalize_tipo(tipo)
                price = find_in_object(listing, "price")
                if isinstance(price, dict):
                    result["precio"] = parse_num(str(price.get("amount") or price.get("value") or ""))
                    curr = str(price.get("currency", ""))
                    result["moneda"] = "USD" if curr == "USD" else "ARS"
                loc = find_in_object(listing, "location")
                if isinstance(loc, dict):
                    result["barrio"] = str(loc.get("neighborhood") or loc.get("city") or loc.get("name") or "")[:100] or None
                features = find_in_object(listing, "features")
                if isinstance(features, list):
                    for f in features:
                        k = str(f.get("name") or f.get("id") or "").lower()
                        v = str(f.get("value") or "")
                        if "ambiente" in k:
                            result["ambientes"] = int(v) if v.isdigit() else None
                        elif "dormitorio" in k or "habitaci" in k:
                            result["dormitorios"] = int(v) if v.isdigit() else None
                        elif "baño" in k:
                            result["banos"] = int(v) if v.isdigit() else None
                        elif "sup" in k and "cub" in k:
                            result["sup_cubierta"] = parse_num(v)
                        elif "sup" in k and "tot" in k:
                            result["sup_total"] = parse_num(v)
                desc = str(find_in_object(listing, "description") or "")
                if desc:
                    result["descripcion"] = desc[:500]
        except Exception:
            pass

    if not result.get("precio"):
        pu = first_match(r"USD\s*([\d.,]+)", html, re.IGNORECASE)
        pa = first_match(r"\$\s*([\d.]+)", html)
        if pu:
            result["precio"] = parse_num(pu)
            result["moneda"] = "USD"
        elif pa:
            result["precio"] = parse_num(pa)
            result["moneda"] = "ARS"
    if not result.get("tipo"):
        h1 = first_match(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.IGNORECASE)
        if h1:
            result["tipo"] = normalize_tipo(strip_html(h1))

    return result


# ── Supabase: buscar en propiedades_mercado (fallback para CDH) ───────────────

def fetch_from_supabase(fuente: str, fuente_id: str) -> Optional[dict]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    url = (
        f"{SUPABASE_URL}/rest/v1/propiedades_mercado"
        f"?fuente=eq.{fuente}&fuente_id=eq.{fuente_id}&select=*&limit=1"
    )
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            rows = json.loads(resp.read())
            if rows:
                row = rows[0]
                return {
                    "tipo": normalize_tipo(str(row.get("tipologia") or "")) or None,
                    "barrio": row.get("zona"),
                    "dormitorios": int(row["dormitorios"]) if row.get("dormitorios") else None,
                    "sup_total": float(row["metros_totales"]) if row.get("metros_totales") else None,
                    "precio": int(row["precio_usd"]) if row.get("precio_usd") else None,
                    "moneda": "USD" if row.get("precio_usd") else None,
                    "descripcion": row.get("titulo"),
                    "imagenes": [row["imagen_url"]] if row.get("imagen_url") else None,
                }
    except Exception as e:
        print(f"Supabase fallback error: {e}")
    return None


# ── HTTP Server ────────────────────────────────────────────────────────────────

class PropertyHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def send_json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Health check
        if parsed.path == "/health":
            self.send_json(200, {"status": "ok"})
            return

        if parsed.path != "/property":
            self.send_json(404, {"error": "Ruta no encontrada"})
            return

        params = urllib.parse.parse_qs(parsed.query)
        prop_url = (params.get("url") or [""])[0].strip()

        if not prop_url:
            self.send_json(400, {"error": "Parámetro 'url' requerido"})
            return

        try:
            urllib.parse.urlparse(prop_url).scheme  # validación básica
        except Exception:
            self.send_json(400, {"error": "URL inválida"})
            return

        portal = detect_portal(prop_url)
        if portal == "unknown":
            self.send_json(422, {"error": "Portal no soportado. Usar MercadoLibre, CasasDeHoy, Zonaprop o Argenprop."})
            return

        print(f"Scraping [{portal}]: {prop_url}")

        # CasasDeHoy: primero buscar en Supabase (el portal bloquea IPs cloud)
        if portal == "casasdehoy":
            cdh_match = re.search(r"-(\d+)-\d+\.html$", prop_url, re.IGNORECASE)
            if cdh_match:
                db_data = fetch_from_supabase("casasdehoy", cdh_match.group(1))
                if db_data:
                    print(f"  → Encontrado en Supabase (CDH {cdh_match.group(1)})")
                    self.send_json(200, clean_result(db_data))
                    return

        # MercadoLibre: intentar API pública primero
        if portal == "mercadolibre":
            ml_match = re.search(r"MLA[-\s]?(\d+)", prop_url, re.IGNORECASE)
            if ml_match:
                ml_id = f"MLA{ml_match.group(1)}"
                api_req = urllib.request.Request(
                    f"https://api.mercadolibre.com/items/{ml_id}",
                    headers={"Accept": "application/json"}
                )
                try:
                    with urllib.request.urlopen(api_req, timeout=10) as resp:
                        item = json.loads(resp.read())
                        data = parse_ml_api(item)
                        print(f"  → Obtenido via ML API ({ml_id})")
                        self.send_json(200, clean_result(data))
                        return
                except Exception as e:
                    print(f"  ML API falló ({e}), cayendo a scraping HTML")

        # Scraping HTML
        referer_map = {
            "casasdehoy": "https://www.casasdehoy.com.ar/",
            "mercadolibre": "https://www.mercadolibre.com.ar/",
            "zonaprop": "https://www.zonaprop.com.ar/",
            "argenprop": "https://www.argenprop.com/",
        }
        html = fetch_html(prop_url, referer=referer_map.get(portal))
        if not html:
            self.send_json(502, {"error": "No se pudo obtener la página"})
            return

        parsers = {
            "casasdehoy": parse_casasdehoy,
            "mercadolibre": parse_mercadolibre_html,
            "zonaprop": parse_zonaprop,
            "argenprop": parse_argenprop,
        }
        data = parsers[portal](html)
        self.send_json(200, clean_result(data))


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== Servidor on-demand fichas ===")
    print(f"Puerto: {PORT}")
    print(f"CORS origin: {ALLOWED_ORIGIN}")
    print(f"Supabase: {'configurado' if SUPABASE_URL else 'no configurado (sin fallback CDH)'}")
    server = HTTPServer(("0.0.0.0", PORT), PropertyHandler)
    print(f"Listo en http://0.0.0.0:{PORT}/property?url=...")
    server.serve_forever()
