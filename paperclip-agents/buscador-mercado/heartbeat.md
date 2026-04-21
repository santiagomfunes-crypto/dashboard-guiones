# Heartbeat — Agente Buscador de Mercado

## Cuándo actúa

On-demand o cuando el CEO / Arquitecto lo despierta con un issue de scraping.

Las routines de scraping automático ya están configuradas en Paperclip:
- CasasDeHoy: diario 6:30am Buenos Aires (routine `569fb876`)
- MercadoLibre: diario 6am Buenos Aires (routine `d7fe3e2b`)

Cuando el agente despierta por una routine, ejecuta el scraper correspondiente. Cuando despierta por issue, sigue las instrucciones del issue.

## 1. Wake-up check

- [ ] ¿Qué me despertó? (leer `PAPERCLIP_WAKE_REASON` o el issue asignado)
- [ ] Si fue routine de CasasDeHoy → ejecutar `scraper_casasdehoy.py`
- [ ] Si fue routine de MercadoLibre → ejecutar `scraper_mercadolibre.py`
- [ ] Si fue issue manual → leer descripción y ejecutar lo que indica

## 2. Ejecutar scraper

### CasasDeHoy
```bash
cd /Users/santiagofunes/Desktop/herramientas/inmobiliaria/guiones
python3 scraper_casasdehoy.py
```
Script: hace upsert en `propiedades_mercado`, deduplica por URL, marca `found_at`.

### MercadoLibre
```bash
cd /Users/santiagofunes/Desktop/herramientas/inmobiliaria/guiones
python3 scraper_mercadolibre.py
```
Script: idem. Marca `fuente: mercadolibre`.

## 3. Verificar resultado

Después de correr el script:
```
GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/propiedades_mercado?select=count
Headers: apikey + Authorization: Bearer sb_publishable_HmiBL9VpEhaYyPqjA1v67w_F38x48El
```
- Comparar con conteo anterior — ¿cuántas propiedades nuevas se agregaron?
- Si el script falló (error de red, parsing roto, etc.) → reportar el error en el issue

## 4. Reportar en Supabase

```
POST https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/reportes
Body: {
  "titulo": "Buscador-Mercado: scraping [fuente] — dd/mm/aaaa",
  "agente": "Buscador-Mercado",
  "contenido": "Total propiedades en DB: X. Nuevas esta corrida: Y. Fuente: Z. Errores: ninguno / [detalle]."
}
```

## 5. Marcar issue como done

Solo si el script terminó sin errores y el conteo en Supabase es coherente.

## Credenciales

```
SUPABASE_URL: https://pgnmpxqljxrpnvexcygh.supabase.co
SUPABASE_KEY: sb_publishable_HmiBL9VpEhaYyPqjA1v67w_F38x48El
```
(Leer SERVICE_KEY de `.env` si necesitás writes con privilegios mayores.)
