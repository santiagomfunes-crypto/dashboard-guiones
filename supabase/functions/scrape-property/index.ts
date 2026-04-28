// Supabase Edge Function: scrape-property
// Recibe { url: string } y extrae datos de una propiedad inmobiliaria.
// Portales soportados: MercadoLibre, CasasDeHoy, Zonaprop, Argenprop

const ALLOWED_ORIGIN = "https://santiagomfunes-crypto.github.io";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, Content-Type",
};

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

function fetchHeaders(referer?: string): Record<string, string> {
  return {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": referer ? "same-origin" : "none",
    "Upgrade-Insecure-Requests": "1",
    ...(referer ? { "Referer": referer } : {}),
  };
}

// ── Tipos ──────────────────────────────────────────────────────────────────────

interface PropertyData {
  tipo?: string;
  barrio?: string;
  ambientes?: number;
  dormitorios?: number;
  banos?: number;
  supCubierta?: number;
  supTotal?: number;
  precio?: number;
  moneda?: "USD" | "ARS";
  descripcion?: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function detectPortal(url: string): string {
  if (url.includes("mercadolibre.com.ar")) return "mercadolibre";
  if (url.includes("casasdehoy.com.ar")) return "casasdehoy";
  if (url.includes("zonaprop.com.ar")) return "zonaprop";
  if (url.includes("argenprop.com")) return "argenprop";
  return "unknown";
}

function parseNum(s: string | undefined | null): number | undefined {
  if (!s) return undefined;
  const clean = s.replace(/[^\d.,]/g, "").replace(",", ".");
  const n = parseFloat(clean);
  return isNaN(n) ? undefined : n;
}

function stripHtml(s: string): string {
  return s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function first(regex: RegExp, text: string, group = 1): string | undefined {
  const m = regex.exec(text);
  return m ? m[group] : undefined;
}

// Normaliza tipo de propiedad al vocabulario del negocio
function normalizeTipo(raw: string): string {
  const r = raw.toLowerCase();
  if (r.includes("departamento") || r.includes("depto") || r.includes("apartment")) return "departamento";
  if (r.includes("ph")) return "PH";
  if (r.includes("local") || r.includes("comercial")) return "local";
  if (r.includes("terreno") || r.includes("lote")) return "terreno";
  if (r.includes("oficina")) return "oficina";
  if (r.includes("casa") || r.includes("house") || r.includes("chalet")) return "casa";
  return raw;
}

// ── Parsers por portal ─────────────────────────────────────────────────────────

// MercadoLibre: API pública /items/{id}
function parseMercadoLibreApi(item: Record<string, unknown>): PropertyData {
  const result: PropertyData = {};

  // Precio
  const price = item.price as number | undefined;
  const currency = item.currency_id as string | undefined;
  if (price) {
    result.precio = price;
    result.moneda = currency === "USD" ? "USD" : "ARS";
  }

  // Título → tipo
  const title = String(item.title || "");
  if (title) result.tipo = normalizeTipo(title);

  // Descripción básica desde título
  result.descripcion = title;

  // Atributos
  const attrs = (item.attributes as Array<Record<string, unknown>>) || [];
  for (const a of attrs) {
    const id = String(a.id || "").toUpperCase();
    const val = String(a.value_name || a.value_struct?.number || "");
    switch (id) {
      case "BEDROOMS": result.dormitorios = parseInt(val) || undefined; break;
      case "ROOMS": result.ambientes = parseInt(val) || undefined; break;
      case "BATHROOMS": result.banos = parseInt(val) || undefined; break;
      case "COVERED_AREA": result.supCubierta = parseNum(val); break;
      case "TOTAL_AREA": result.supTotal = parseNum(val); break;
      case "PROPERTY_TYPE": if (val) result.tipo = normalizeTipo(val); break;
      case "NEIGHBORHOOD": if (val) result.barrio = val; break;
    }
  }

  // Location
  const loc = item.location as Record<string, unknown> | undefined;
  if (loc && !result.barrio) {
    result.barrio = String(
      (loc.neighborhood as Record<string, unknown>)?.name ||
      (loc.city as Record<string, unknown>)?.name || ""
    ) || undefined;
  }

  return result;
}

// MercadoLibre: individual property page (HTML) (HTML fallback)
// La data está en window.__PRELOADED_STATE__ o en JSON-LD
function parseMercadoLibre(html: string): PropertyData {
  const result: PropertyData = {};

  // Intentar JSON-LD primero (schema.org)
  const jsonLdMatch = html.match(/<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi);
  if (jsonLdMatch) {
    for (const block of jsonLdMatch) {
      const inner = block.replace(/<script[^>]*>/, "").replace(/<\/script>/, "");
      try {
        const data = JSON.parse(inner);
        if (data["@type"] && (data.name || data.description)) {
          if (data.description) result.descripcion = data.description.substring(0, 500);
        }
      } catch (_) { /* ignorar */ }
    }
  }

  // Extraer __PRELOADED_STATE__ para datos estructurados
  const stateMatch = html.match(/window\.__PRELOADED_STATE__\s*=\s*(\{[\s\S]*?\});\s*<\/script>/);
  if (stateMatch) {
    try {
      const state = JSON.parse(stateMatch[1]);
      // Navegar la estructura de ML
      const vip = state?.initialState?.components?.["pi-preloaded-components"] ||
                  state?.initialState?.components || {};
      // intentar extraer atributos
      const attrs = findInObject(state, "attributes") as Record<string, unknown>[] | undefined;
      if (Array.isArray(attrs)) {
        for (const attr of attrs) {
          const id = String(attr.id || "").toLowerCase();
          const val = String(attr.value_name || attr.value || "");
          if (id.includes("dormitorio") || id.includes("bedroom")) {
            result.dormitorios = parseInt(val) || undefined;
          }
          if (id.includes("ambiente")) {
            result.ambientes = parseInt(val) || undefined;
          }
          if (id.includes("baño") || id.includes("bathroom")) {
            result.banos = parseInt(val) || undefined;
          }
          if (id.includes("sup") && id.includes("cub")) {
            result.supCubierta = parseNum(val);
          }
          if (id.includes("sup") && id.includes("tot")) {
            result.supTotal = parseNum(val);
          }
        }
      }
    } catch (_) { /* ignorar */ }
  }

  // Fallback con regex directamente en HTML

  // Precio
  const precioUsd = first(/\$\s*USD\s*([\d.,]+)/i, html) || first(/USD\s*([\d.,]+)/i, html);
  const precioArs = first(/\$\s*ARS\s*([\d.,]+)/i, html) || first(/\$\s*([\d.]+)\s*(?:por mes)?/i, html);
  if (precioUsd) {
    result.precio = parseNum(precioUsd);
    result.moneda = "USD";
  } else if (precioArs) {
    result.precio = parseNum(precioArs);
    result.moneda = "ARS";
  }

  // Tipo desde breadcrumb o título
  const tipoMatch = first(/<h1[^>]*class="[^"]*ui-pdp-title[^"]*"[^>]*>(.*?)<\/h1>/i, html);
  if (tipoMatch) {
    const clean = stripHtml(tipoMatch);
    result.tipo = normalizeTipo(clean);
    if (!result.descripcion) result.descripcion = clean;
  }

  // Barrio / ubicación
  const barrioMatch = first(/class="[^"]*map__link[^"]*"[^>]*>(.*?)<\/a>/i, html) ||
                      first(/"neighborhood"\s*:\s*"([^"]+)"/i, html);
  if (barrioMatch) result.barrio = stripHtml(barrioMatch);

  // Ambientes, dormitorios, baños desde la tabla de atributos
  if (!result.ambientes) {
    const m = first(/(\d+)\s*ambiente/i, html);
    if (m) result.ambientes = parseInt(m);
  }
  if (!result.dormitorios) {
    const m = first(/(\d+)\s*dormitorio/i, html);
    if (m) result.dormitorios = parseInt(m);
  }
  if (!result.banos) {
    const m = first(/(\d+)\s*ba[ñn]o/i, html);
    if (m) result.banos = parseInt(m);
  }
  if (!result.supCubierta) {
    const m = first(/([\d.,]+)\s*m²\s*cub/i, html);
    if (m) result.supCubierta = parseNum(m);
  }
  if (!result.supTotal) {
    const m = first(/([\d.,]+)\s*m²\s*tot/i, html) || first(/([\d.,]+)\s*m²/i, html);
    if (m) result.supTotal = parseNum(m);
  }

  return result;
}

// CasasDeHoy: detalle de propiedad
function parseCasasDeHoy(html: string): PropertyData {
  const result: PropertyData = {};

  // Título principal
  const titulo = first(/<h1[^>]*>([\s\S]*?)<\/h1>/i, html);
  if (titulo) {
    const clean = stripHtml(titulo);
    result.tipo = normalizeTipo(clean);
    result.descripcion = clean;
  }

  // Precio
  const precioUsd = first(/U\$S\s*([\d.,]+)/i, html);
  const precioArs = first(/\$\s*([\d.,]+)/i, html);
  if (precioUsd) {
    result.precio = parseNum(precioUsd);
    result.moneda = "USD";
  } else if (precioArs) {
    result.precio = parseNum(precioArs);
    result.moneda = "ARS";
  }

  // Metros
  const m2Cub = first(/([\d.,]+)\s*m²?\s*cub/i, html) || first(/cubiertos?[^<]*?([\d.,]+)/i, html);
  if (m2Cub) result.supCubierta = parseNum(m2Cub);

  const m2Tot = first(/([\d.,]+)\s*m²?\s*tot/i, html) || first(/totales?[^<]*?([\d.,]+)/i, html);
  if (m2Tot) result.supTotal = parseNum(m2Tot);

  // Dormitorios
  const dorms = first(/(\d+)\s*dormitorio/i, html) || first(/(\d+)\s*habitaci/i, html);
  if (dorms) result.dormitorios = parseInt(dorms);

  // Ambientes
  const amb = first(/(\d+)\s*ambiente/i, html);
  if (amb) result.ambientes = parseInt(amb);

  // Baños
  const banos = first(/(\d+)\s*ba[ñn]o/i, html);
  if (banos) result.banos = parseInt(banos);

  // Barrio / zona
  const barrio = first(/<p[^>]*class="[^"]*zona[^"]*"[^>]*>([\s\S]*?)<\/p>/i, html) ||
                 first(/Tandil[^,]*,?\s*([^<\n]+)/i, html);
  if (barrio) result.barrio = stripHtml(barrio).substring(0, 100);

  // Descripción larga
  const desc = first(/<div[^>]*class="[^"]*descripcion[^"]*"[^>]*>([\s\S]*?)<\/div>/i, html);
  if (desc) result.descripcion = stripHtml(desc).substring(0, 500);

  return result;
}

// Zonaprop: scraper para fichas individuales
function parseZonaprop(html: string): PropertyData {
  const result: PropertyData = {};

  // JSON-LD con schema.org
  const jsonLdBlocks = html.match(/<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi) || [];
  for (const block of jsonLdBlocks) {
    const inner = block.replace(/<script[^>]*>/i, "").replace(/<\/script>/i, "");
    try {
      const data = JSON.parse(inner);
      if (data.description) result.descripcion = data.description.substring(0, 500);
      if (data.name) result.tipo = normalizeTipo(data.name);
      // numberOfRooms, numberOfBedrooms, numberOfBathroomsTotal
      if (data.numberOfRooms) result.ambientes = parseInt(data.numberOfRooms);
      if (data.numberOfBedrooms) result.dormitorios = parseInt(data.numberOfBedrooms);
      if (data.numberOfBathroomsTotal) result.banos = parseInt(data.numberOfBathroomsTotal);
      if (data.floorSize?.value) result.supCubierta = parseNum(String(data.floorSize.value));
      if (data.address?.addressLocality) result.barrio = data.address.addressLocality;
      // Precio
      if (data.offers) {
        const offers = Array.isArray(data.offers) ? data.offers[0] : data.offers;
        if (offers?.price) {
          result.precio = parseNum(String(offers.price));
          result.moneda = offers.priceCurrency === "USD" ? "USD" : "ARS";
        }
      }
    } catch (_) { /* ignorar */ }
  }

  // Extraer estado de preloaded state de Zonaprop (Next.js __NEXT_DATA__)
  const nextDataMatch = html.match(/<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i);
  if (nextDataMatch) {
    try {
      const nd = JSON.parse(nextDataMatch[1]);
      const listing = findInObject(nd, "listing") as Record<string, unknown> | undefined;
      if (listing) {
        const attrs = findInObject(listing, "attributes") as Record<string, unknown>[] | undefined;
        if (Array.isArray(attrs)) {
          for (const a of attrs) {
            const id = String(a.id || "").toLowerCase();
            const val = String(a.value || "");
            if (id === "total_area") result.supTotal = parseNum(val);
            if (id === "covered_area") result.supCubierta = parseNum(val);
            if (id === "rooms") result.ambientes = parseInt(val) || undefined;
            if (id === "bedrooms") result.dormitorios = parseInt(val) || undefined;
            if (id === "bathrooms") result.banos = parseInt(val) || undefined;
          }
        }
        // Precio
        const priceData = findInObject(listing, "price") as Record<string, unknown> | undefined;
        if (priceData && !result.precio) {
          result.precio = parseNum(String(priceData.amount || priceData.value || ""));
          const curr = String(priceData.currency || "");
          result.moneda = curr === "USD" ? "USD" : "ARS";
        }
        // Barrio
        const loc = findInObject(listing, "location") as Record<string, unknown> | undefined;
        if (loc && !result.barrio) {
          result.barrio = String(loc.name || loc.neighborhood || "").substring(0, 100) || undefined;
        }
        // Tipo
        const propType = findInObject(listing, "propertyType") as string | undefined;
        if (propType && !result.tipo) result.tipo = normalizeTipo(propType);
      }
    } catch (_) { /* ignorar */ }
  }

  // Fallback regex
  if (!result.precio) {
    const pu = first(/USD\s*([\d.,]+)/i, html) || first(/U\$S\s*([\d.,]+)/i, html);
    const pa = first(/\$\s*([\d.]+)/i, html);
    if (pu) { result.precio = parseNum(pu); result.moneda = "USD"; }
    else if (pa) { result.precio = parseNum(pa); result.moneda = "ARS"; }
  }
  if (!result.ambientes) {
    const m = first(/(\d+)\s*ambiente/i, html);
    if (m) result.ambientes = parseInt(m);
  }
  if (!result.dormitorios) {
    const m = first(/(\d+)\s*dormitorio/i, html);
    if (m) result.dormitorios = parseInt(m);
  }
  if (!result.banos) {
    const m = first(/(\d+)\s*ba[ñn]o/i, html);
    if (m) result.banos = parseInt(m);
  }
  if (!result.supCubierta) {
    const m = first(/([\d.,]+)\s*m[²2]\s*cub/i, html);
    if (m) result.supCubierta = parseNum(m);
  }
  if (!result.supTotal) {
    const m = first(/([\d.,]+)\s*m[²2]\s*tot/i, html);
    if (m) result.supTotal = parseNum(m);
  }
  if (!result.tipo) {
    const t = first(/class="[^"]*property-type[^"]*"[^>]*>([\s\S]*?)<\//, html) ||
              first(/<h1[^>]*>([\s\S]*?)<\/h1>/i, html);
    if (t) result.tipo = normalizeTipo(stripHtml(t));
  }

  return result;
}

// Argenprop: scraper para fichas individuales
function parseArgenprop(html: string): PropertyData {
  const result: PropertyData = {};

  // __NEXT_DATA__ (Next.js)
  const nextDataMatch = html.match(/<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i);
  if (nextDataMatch) {
    try {
      const nd = JSON.parse(nextDataMatch[1]);
      const listing = findInObject(nd, "data") as Record<string, unknown> | undefined ||
                      findInObject(nd, "property") as Record<string, unknown> | undefined;
      if (listing) {
        // Tipo
        const tipo = String(
          findInObject(listing, "propertyType") ||
          findInObject(listing, "type") || ""
        );
        if (tipo) result.tipo = normalizeTipo(tipo);

        // Precio
        const price = findInObject(listing, "price") as Record<string, unknown> | undefined;
        if (price) {
          result.precio = parseNum(String(price.amount || price.value || ""));
          const curr = String(price.currency || "");
          result.moneda = curr === "USD" ? "USD" : "ARS";
        }

        // Barrio
        const loc = findInObject(listing, "location") as Record<string, unknown> | undefined;
        if (loc) {
          result.barrio = String(
            loc.neighborhood || loc.city || loc.name || ""
          ).substring(0, 100) || undefined;
        }

        // Atributos
        const features = findInObject(listing, "features") as Record<string, unknown>[] | undefined;
        if (Array.isArray(features)) {
          for (const f of features) {
            const k = String(f.name || f.id || "").toLowerCase();
            const v = String(f.value || "");
            if (k.includes("ambiente")) result.ambientes = parseInt(v) || undefined;
            if (k.includes("dormitorio") || k.includes("habitaci")) result.dormitorios = parseInt(v) || undefined;
            if (k.includes("baño")) result.banos = parseInt(v) || undefined;
            if (k.includes("sup") && k.includes("cub")) result.supCubierta = parseNum(v);
            if (k.includes("sup") && k.includes("tot")) result.supTotal = parseNum(v);
          }
        }

        // Descripción
        const desc = String(findInObject(listing, "description") || "");
        if (desc) result.descripcion = desc.substring(0, 500);
      }
    } catch (_) { /* ignorar */ }
  }

  // Fallback regex
  if (!result.precio) {
    const pu = first(/USD\s*([\d.,]+)/i, html) || first(/U\$S\s*([\d.,]+)/i, html);
    const pa = first(/\$\s*([\d.]+)/i, html);
    if (pu) { result.precio = parseNum(pu); result.moneda = "USD"; }
    else if (pa) { result.precio = parseNum(pa); result.moneda = "ARS"; }
  }
  if (!result.tipo) {
    const t = first(/<h1[^>]*>([\s\S]*?)<\/h1>/i, html);
    if (t) result.tipo = normalizeTipo(stripHtml(t));
  }
  if (!result.ambientes) {
    const m = first(/(\d+)\s*ambiente/i, html);
    if (m) result.ambientes = parseInt(m);
  }
  if (!result.dormitorios) {
    const m = first(/(\d+)\s*dormitorio/i, html);
    if (m) result.dormitorios = parseInt(m);
  }
  if (!result.banos) {
    const m = first(/(\d+)\s*ba[ñn]o/i, html);
    if (m) result.banos = parseInt(m);
  }
  if (!result.supCubierta) {
    const m = first(/([\d.,]+)\s*m[²2]\s*cub/i, html);
    if (m) result.supCubierta = parseNum(m);
  }
  if (!result.supTotal) {
    const m = first(/([\d.,]+)\s*m[²2]\s*tot/i, html);
    if (m) result.supTotal = parseNum(m);
  }

  return result;
}

// ── Utilidad: buscar un campo por nombre en un objeto anidado ──────────────────

function findInObject(obj: unknown, key: string, depth = 0): unknown {
  if (depth > 8) return undefined;
  if (!obj || typeof obj !== "object") return undefined;
  if (Array.isArray(obj)) {
    for (const item of obj) {
      const found = findInObject(item, key, depth + 1);
      if (found !== undefined) return found;
    }
    return undefined;
  }
  const record = obj as Record<string, unknown>;
  if (key in record) return record[key];
  for (const v of Object.values(record)) {
    const found = findInObject(v, key, depth + 1);
    if (found !== undefined) return found;
  }
  return undefined;
}

// ── Limpieza del resultado: eliminar campos undefined/null ─────────────────────

function cleanResult(data: PropertyData): Partial<PropertyData> {
  const out: Partial<PropertyData> = {};
  for (const [k, v] of Object.entries(data)) {
    if (v !== undefined && v !== null && v !== "" && !isNaN(v as number)) {
      (out as Record<string, unknown>)[k] = v;
    }
  }
  return out;
}

// ── Handler principal ──────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Método no permitido" }), {
      status: 405,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  let url: string;
  try {
    const body = await req.json();
    url = body?.url?.trim();
    if (!url) throw new Error("url requerida");
    new URL(url); // valida formato
  } catch (e) {
    return new Response(JSON.stringify({ error: `Body inválido: ${(e as Error).message}` }), {
      status: 400,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  const portal = detectPortal(url);
  if (portal === "unknown") {
    return new Response(
      JSON.stringify({ error: "Portal no soportado. Usar MercadoLibre, CasasDeHoy, Zonaprop o Argenprop." }),
      { status: 422, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
    );
  }

  // Para MercadoLibre: intentar API pública primero si es una URL de item
  if (portal === "mercadolibre") {
    const mlIdMatch = url.match(/MLA[-\s]?(\d+)/i);
    if (mlIdMatch) {
      const mlId = `MLA${mlIdMatch[1]}`;
      try {
        const apiResp = await fetch(`https://api.mercadolibre.com/items/${mlId}`, {
          headers: { "Accept": "application/json" },
          signal: AbortSignal.timeout(10_000),
        });
        if (apiResp.ok) {
          const item = await apiResp.json() as Record<string, unknown>;
          const data = parseMercadoLibreApi(item);
          return new Response(JSON.stringify(cleanResult(data)), {
            status: 200,
            headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
          });
        }
      } catch (_) { /* caer a scraping HTML */ }
    }
  }

  // Fetch de la página
  let html: string;
  try {
    const refererMap: Record<string, string> = {
      zonaprop: "https://www.zonaprop.com.ar/",
      argenprop: "https://www.argenprop.com/",
      mercadolibre: "https://www.mercadolibre.com.ar/",
      casasdehoy: "https://www.casasdehoy.com.ar/",
    };
    const resp = await fetch(url, {
      headers: fetchHeaders(refererMap[portal]),
      redirect: "follow",
      signal: AbortSignal.timeout(15_000),
    });
    if (!resp.ok) {
      return new Response(
        JSON.stringify({ error: `El portal devolvió HTTP ${resp.status}` }),
        { status: 502, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
      );
    }
    html = await resp.text();
  } catch (e) {
    return new Response(
      JSON.stringify({ error: `Error al obtener la URL: ${(e as Error).message}` }),
      { status: 502, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
    );
  }

  // Parseo según portal
  let data: PropertyData;
  switch (portal) {
    case "mercadolibre":
      data = parseMercadoLibre(html);
      break;
    case "casasdehoy":
      data = parseCasasDeHoy(html);
      break;
    case "zonaprop":
      data = parseZonaprop(html);
      break;
    case "argenprop":
      data = parseArgenprop(html);
      break;
    default:
      data = {};
  }

  const result = cleanResult(data);

  return new Response(JSON.stringify(result), {
    status: 200,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
});
