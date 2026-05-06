# Handoff técnico — Santiago Funes RE
## Para Agentix: cambio de frontend

*Documento de referencia para el equipo que reimplementa el sitio web.*

---

## 1. Arquitectura actual

El sistema tiene **dos proyectos Supabase separados** con roles distintos. Confundirlos es el error más común.

| Proyecto | URL | Para qué se usa |
|---|---|---|
| **sfre-web** (el sitio) | `https://bsvcorcwcijpvwzxjzgu.supabase.co` | Propiedades publicadas, imágenes, newsletter |
| **guiones** (dashboard interno) | `https://pgnmpxqljxrpnvexcygh.supabase.co` | Guiones de contenido, scrapers de mercado — uso interno, NO tocar |

**El nuevo frontend solo necesita conectarse al proyecto `bsvcorcwcijpvwzxjzgu`.**

---

## 2. Credenciales del proyecto sfre-web

```
NEXT_PUBLIC_SUPABASE_URL=https://bsvcorcwcijpvwzxjzgu.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzdmNvcmN3Y2lqcHZ3enhqemd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2NDA5NzAsImV4cCI6MjA5MzIxNjk3MH0.TZOpZrQWx-rimFw7O1bezFbrgfE6Mc_S2hkf5WJbl9k
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzdmNvcmN3Y2lqcHZ3enhqemd1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NzY0MDk3MCwiZXhwIjoyMDkzMjE2OTcwfQ.9pilKk7-8piGdJUZCLDHKhaYkQKQAVS4W-aTWUQTgKo
ADMIN_PASSWORD=altavista2026
NEXT_PUBLIC_SITE_URL=https://propiedades.santiagofunes.com.ar
```

- **Anon Key**: para lectura pública desde el cliente (React/browser)
- **Service Role Key**: para escritura desde el servidor (API routes, N8N, bots). Nunca exponerla en el frontend.

---

## 3. Tabla principal: `propiedades`

**Proyecto:** `bsvcorcwcijpvwzxjzgu`
**Schema:** `public`
**Query básica:**

```sql
SELECT * FROM propiedades
WHERE estado = 'disponible'
ORDER BY created_at DESC;
```

### Campos de la tabla

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | uuid | PK, generado automáticamente |
| `slug` | text | URL amigable — único. Ej: `departamento-garibaldi-431-1mb4x` |
| `titulo` | text | Título de la propiedad |
| `tipo` | text | `Departamento`, `Casa`, `Lote`, `Fideicomiso`, etc. |
| `estado` | text | `disponible` o `no_disponible` |
| `modalidad` | text | `venta` o `alquiler` |
| `dormitorios` | text | Texto libre: `"1"`, `"2"`, `"Monoambiente"` |
| `banos` | text | Cantidad de baños |
| `superficie` | text | Ej: `"48 m²"` |
| `posicion` | text | `"Frente"`, `"Contrafrente"`, `"Indistinto"` |
| `piso` | text | Número de piso |
| `cochera` | text | `"Con cochera"` o `"Sin cochera"` |
| `descripcion` | text | Texto descriptivo de la propiedad |
| `precio` | text | Ej: `"USD 102.500"` o `"$ 450.000"` |
| `imagenes` | text[] | Array de URLs públicas de Supabase Storage |
| `lat` | float8 | Latitud (opcional, para mapa) |
| `lng` | float8 | Longitud (opcional, para mapa) |
| `edificio` | text | Nombre del edificio (para agrupar unidades). Ej: `"Garibaldi 431"` |
| `created_at` | timestamptz | Fecha de carga |

### Lógica de agrupación por edificio

Las propiedades con el mismo valor en el campo `edificio` se agrupan y muestran como una sola card en el listado, con el precio mínimo/máximo y cantidad de unidades disponibles. Las propiedades sin `edificio` se muestran individualmente.

---

## 4. Storage de imágenes

**Bucket:** `propiedades` (en el proyecto `bsvcorcwcijpvwzxjzgu`)
**Acceso:** público
**URL pública:** `https://bsvcorcwcijpvwzxjzgu.supabase.co/storage/v1/object/public/propiedades/{filename}`

Las URLs ya se guardan completas en el campo `imagenes[]` de cada propiedad. No hace falta construirlas manualmente.

---

## 5. API Routes del sitio actual (Next.js)

El sitio actual corre en Vercel en `https://propiedades.santiagofunes.com.ar`. Estas son las rutas de API disponibles — el nuevo frontend puede reutilizarlas o reimplementarlas.

### Propiedades

| Método | Ruta | Autenticación | Descripción |
|---|---|---|---|
| `POST` | `/api/admin/propiedades` | Cookie `admin_token` | Crear propiedad nueva |
| `PATCH` | `/api/admin/propiedades/{id}` | Cookie `admin_token` | Editar propiedad existente |
| `DELETE` | `/api/admin/propiedades/{id}` | Cookie `admin_token` | Eliminar propiedad |

### Imágenes

| Método | Ruta | Autenticación | Descripción |
|---|---|---|---|
| `POST` | `/api/admin/upload` | Cookie `admin_token` | Subir imagen → devuelve URL pública |

### Admin / Sesión

| Método | Ruta | Body | Descripción |
|---|---|---|---|
| `POST` | `/api/admin/login` | `{ password }` | Login → setea cookie `admin_token` |
| `DELETE` | `/api/admin/login` | — | Logout |

**Password actual:** `altavista2026`
**Autenticación:** cookie httpOnly `admin_token` (sin JWT, sin Supabase Auth).

### Herramientas de carga

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/admin/scrape-preview` | Recibe una URL de portal (ZonaProp, Argenprop, MercadoLibre, etc.) y devuelve los datos estructurados de la propiedad para pre-rellenar el formulario |
| `POST` | `/api/admin/analizar-lote` | Recibe imagen en base64, usa Claude AI para extraer datos del lote |
| `POST` | `/api/admin/generar-ficha` | Agrega una URL de ficha PDF al array de imágenes de una propiedad |

### Otros

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/newsletter/subscribe` | Suscribir email a tabla `newsletter_suscriptores` |
| `GET` | `/api/mercado/stats` | Estadísticas del mercado inmobiliario Tandil (desde proyecto `pgnmpxqljxrpnvexcygh`) |

---

## 6. Otras tablas en `bsvcorcwcijpvwzxjzgu`

| Tabla | Para qué se usa |
|---|---|
| `propiedades` | Las 40 propiedades publicadas en el sitio |
| `newsletter_suscriptores` | Emails captados desde el sitio. Campos: `email`, `nombre`, `created_at` |

---

## 7. Qué NO usar / aclaraciones importantes

- **No usar la tabla `publicaciones`** del proyecto `pgnmpxqljxrpnvexcygh` — es el calendario editorial de contenido de redes sociales, no tiene propiedades inmobiliarias.
- **No usar la tabla `propiedades_mercado`** — son datos scrapeados de portales (ZonaProp, MercadoLibre, etc.) para análisis de mercado interno. No son propiedades de la agencia.
- El dominio actual es `propiedades.santiagofunes.com.ar` con DNS en Cloudflare apuntando a Vercel. Al migrar hay que actualizar solo el registro DNS en Cloudflare.
- El bot/N8N que consume propiedades debe conectarse a `bsvcorcwcijpvwzxjzgu`, tabla `propiedades`, con la Service Role Key si necesita escribir o la Anon Key si solo lee.

---

## 8. Cómo crear/editar una propiedad desde N8N o un bot externo

Sin pasar por el panel admin, se puede insertar directo a Supabase vía REST:

```
POST https://bsvcorcwcijpvwzxjzgu.supabase.co/rest/v1/propiedades
Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}
apikey: {SUPABASE_SERVICE_ROLE_KEY}
Content-Type: application/json

{
  "titulo": "Departamento Garibaldi 431",
  "slug": "depto-garibaldi-431-abc123",
  "tipo": "Departamento",
  "estado": "disponible",
  "modalidad": "venta",
  "precio": "USD 100.000",
  "dormitorios": "1",
  "superficie": "48 m²",
  "descripcion": "...",
  "imagenes": ["https://..."],
  "edificio": "Garibaldi 431"
}
```

Para actualizar:
```
PATCH https://bsvcorcwcijpvwzxjzgu.supabase.co/rest/v1/propiedades?id=eq.{uuid}
```

Para listar todas las disponibles:
```
GET https://bsvcorcwcijpvwzxjzgu.supabase.co/rest/v1/propiedades?estado=eq.disponible&order=created_at.desc
Authorization: Bearer {SUPABASE_ANON_KEY}
apikey: {SUPABASE_ANON_KEY}
```

---

*Generado 04/05/2026 — Santiago Funes RE / Grupo Alta Vista Otero*
