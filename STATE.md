# STATE — Dashboard Guiones SFRE

> Estado vivo del sistema. Las decisiones e instrucciones importantes van ACÁ, no en el chat.
> Si una pestaña de Claude se envenena (autocompact thrashing), releé este archivo y seguí.

## Estructura de archivos (jul 2026)
Ex-monolito `index.html` de 2605 líneas partido en 3 para evitar thrashing de contexto:
- `index.html` (~830 líneas) — markup + login.
- `styles.css` (~330 líneas) — diseño (colores, tipografía, layout).
- `app.js` (~1770 líneas) — motor JS + Supabase.

**Regla:** cambio de diseño = solo `styles.css` (+ markup). Cambio de lógica = solo `app.js`. Nunca abrir el archivo que no toca.

## Cómo probar
```bash
python3 -m http.server 8901
agent-browser open http://localhost:8901/index.html snapshot --json
```
Título esperado: "Guiones — Santiago Funes RE". Login: santiagomfunes@gmail.com / santiago.

## Decisiones tomadas
- Tipografía headings: Cormorant Garamond se mantiene (preferencia explícita de Santiago).
- Único usuario: Santiago. Celina y Marcos fuera desde jul 2026.

## Pendiente / en curso
- [ ] **Rediseño identidad AltaVista Otero**: tema claro, navy + verde, Montserrat + Cormorant Garamond,
      logo en topbar navy. El motor JS (`app.js`) NO se toca. Cambios SOLO en `styles.css` + markup.
      (Venía intentándose cuando la sesión entró en loop de thrashing — nunca se aplicó, index.html quedó intacto.)

## Gestor de documentación de cartera (`documentacion.html`) — jul 2026
Sistema nuevo para la parte administrativa: qué documentación pedir por cada propiedad, qué se pidió, qué llegó y qué falta. Standalone, NO embebido en crm.html (para no inflarlo).

**Arquitectura**
- Página única `documentacion.html` — login gate propio (Supabase Auth, mismo usuario que el CRM).
- Backend Supabase `pgnmpxqljxrpnvexcygh` (mismo proyecto que el dashboard y el CRM). Anon/publishable key en el HTML.
- Tabla `crm_documentos` (una fila por documento por propiedad): `propiedad_id` (→ `crm_propiedades.id`), `tipo_doc`, `estado`, `fecha_solicitado`, `fecha_recibido`, `nota`, `link`, `archivo_path`, `archivo_nombre`.
- Propiedades salen de `crm_propiedades` (`select id,direccion,zona,tipo,estado,operacion order by creado_en`). **Ojo:** la columna de fecha es `creado_en`, NO `created_at` (crm.html tiene ese bug latente, acá está bien).
- Storage: bucket **privado** `documentos` (50MB). Archivos se ven con `createSignedUrl(path, 3600)` (no hay URL pública). Path: `${propId}/${slug}-${timestamp}-${nombreSanitizado}`.

**Pedido al propietario (copy-paste / WhatsApp)** — jul 2026: en el modal de cada propiedad hay dos botones (`copiarPedido()` / `waPedido()`, dorado y verde WA). Arman un mensaje con la documentación que TODAVÍA falta (estado ≠ recibido y ≠ no_aplica), agrupada por categoría, en tono Santi. Propiedad nueva → lista todo; propiedad avanzada → solo lo pendiente. `Copiar` usa clipboard API con fallback execCommand; `WhatsApp` abre `wa.me/?text=` (sin número, Santi elige el contacto). Lógica en `buildPedido()`.

**Checklist (template en el JS, no en DB)** — se filtra por tipo de propiedad vía campo `aplica` ('all' o array):
Titularidad y dominio · Catastro y planos · Impuestos y tasas · Consorcio (solo depto) · Servicios · Comercial.
Estados: `pendiente` (falta pedir) · `solicitado` · `recibido` · `no_aplica`. El progreso = recibidos / aplicables (excluye no_aplica del denominador). Subir un archivo auto-marca `recibido`; cambiar estado auto-setea la fecha del día.

**Cómo probar**
```bash
python3 -m http.server 8891   # desde la carpeta guiones/
agent-browser open http://localhost:8891/documentacion.html console --json
```
Título esperado: "Documentación — Santiago Funes RE". agent-browser NO puede loguearse (no tiene sesión Supabase) → solo sirve para verificar que renderiza el login y que no hay errores de consola. Prueba funcional completa = navegador real logueado.

**Wiring**
- `crm.html` topbar: link `📁 Documentación` (clase `.btn-doc`) antes de "Salir".
- `panel-central.html`: sección "Gestión inmobiliaria" con tiles CRM + Documentación.

**Hosting**: GitHub Pages → `santiagomfunes-crypto.github.io/dashboard-guiones/documentacion.html` (pushear para que quede live).

**Estado backend (verificado jul 8 2026)**: ✅ tabla `crm_documentos` viva · ✅ bucket privado `documentos` creado · ✅ RLS: policy `docs_auth_all` (ALL/authenticated) en la tabla y `docs_obj_all` (ALL/authenticated) en storage.objects · ✅ live en GitHub Pages.

**⚠️ GOTCHA RLS (arreglado jul 8 2026)**: `crm_propiedades` y `crm_contactos` tenían RLS **prendido pero SIN ninguna policy** → `authenticated` no podía leer NADA. La página mostraba "0 propiedades" aunque hubiera datos, y el CRM tampoco leía/escribía. Fix aplicado: `create policy prop_auth_all on crm_propiedades for all to authenticated using(true) with check(true)` (y `cont_auth_all` igual en crm_contactos). Regla: **toda tabla `crm_*` nueva necesita su policy ALL/authenticated o queda muda.**

**Nota de datos**: la documentación se genera POR propiedad leyendo `crm_propiedades`. Si esa tabla está vacía, la página muestra "No hay propiedades". Cargar propiedades desde el CRM → aparecen solas en Documentación con su checklist completo.

**Carga inicial de cartera (jul 8 2026)**: se importaron las **52 propiedades** de la web `propiedades.santiagofunes.com.ar` a `crm_propiedades`. La web usa OTRO Supabase (`bsvcorcwcijpvwzxjzgu`, tabla `propiedades`); se leyó vía Management API (token account-level sirve para ambos proyectos) y se mapeó → `crm_propiedades` (destino `pgnmpxqljxrpnvexcygh`). Mapeo: `titulo→direccion`, `initcap(tipo)→tipo`, `modalidad→operacion`, precio/superficie parseados con regexp a numérico, `dormitorios→ambientes` (si es entero), `estado` tal cual (disponible/reservado/borrador/no_disponible), `url_publicacion='.../propiedades/'||slug`, `notas` con el edificio. `zona` quedó null (la web no la tiene por barrio). Re-correr el import duplicaría: si hay que resincronizar, primero `truncate crm_propiedades` o dedup por `url_publicacion`.

## Backups
- `index.html.bak` — copia del monolito pre-split (redundante con git, borrar cuando el split esté confirmado en prod).
- Git: el monolito original está en el último commit.
