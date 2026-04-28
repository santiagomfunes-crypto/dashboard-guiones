# Servidor on-demand — Fichas de propiedades

Servidor HTTP Python (stdlib pura, sin dependencias) que expone un endpoint para scraping on-demand de fichas de propiedades inmobiliarias.

## Endpoint

```
GET /property?url=<url-de-propiedad>
```

### Portales soportados

- **MercadoLibre** → usa la API pública de ML primero (más rápido y confiable)
- **CasasDeHoy** → primero busca en Supabase `propiedades_mercado`, luego scraping HTML
- **Zonaprop** → scraping HTML + __NEXT_DATA__ JSON
- **Argenprop** → scraping HTML + __NEXT_DATA__ JSON

### Respuesta

```json
{
  "tipo": "casa",
  "barrio": "Centro",
  "ambientes": 4,
  "dormitorios": 3,
  "banos": 2,
  "sup_cubierta": 120,
  "sup_total": 200,
  "precio": 180000,
  "moneda": "USD",
  "descripcion": "...",
  "imagenes": ["https://..."]
}
```

Sólo se incluyen los campos con valor (sin nulls).

## Deploy en Railway

1. Crear nuevo proyecto en Railway
2. Conectar este directorio (`railway-server/`) como raíz del servicio
3. Configurar variables de entorno:
   - `SUPABASE_URL` → `https://pgnmpxqljxrpnvexcygh.supabase.co`
   - `SUPABASE_SERVICE_KEY` → service key de Supabase
   - `ALLOWED_ORIGIN` → `https://santiagomfunes-crypto.github.io` (ya es el default)
4. Railway detecta automáticamente el `Procfile` y arranca el servidor
5. Copiar la URL pública generada por Railway (ej: `https://scraper-fichas.up.railway.app`)

## Health check

```
GET /health
→ {"status": "ok"}
```

## Correr local

```bash
cd railway-server
SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python server.py
# Listo en http://localhost:8080/property?url=...
```
