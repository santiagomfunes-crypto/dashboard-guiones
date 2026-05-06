# Inicio rápido — qué hacer si se reinicia la computadora

> Documento para Santiago. Si se apagó la compu, perdiste el contexto del editor, o simplemente arrancás desde cero, seguí estos pasos en orden.

---

## 1. Abrir el workspace en VS Code

```bash
code /Users/santiagofunes/Desktop/herramientas/inmobiliaria/guiones
```

O desde Finder: `Desktop → herramientas → inmobiliaria → guiones` → clic derecho → "Abrir con VS Code".

Los open editors se restauran solos (VS Code recuerda la sesión). Si no aparecen, abrí manualmente:

| Archivo | Para qué |
|---|---|
| `CLAUDE.md` | Instrucciones del sistema — qué puede hacer Claude Code |
| `railway-server/server.py` | Código de Sofía (el bot de WhatsApp) |
| `referencia/datos-tandil.md` | Datos de mercado Tandil |
| `borradores/prompt-sofia-v2.md` | Prompt de Sofía v2 (backup legible) |
| Cualquier `tasacion-*.html` | Tasaciones de clientes |

---

## 2. Verificar que Sofía sigue viva

```bash
curl https://sofia-bot-production-e17d.up.railway.app/health
```

Debe responder `{"status": "ok"}`. Si no responde: Railway se habrá dormido (plan free) → entrá a railway.app → proyecto `sofia-bot` → clic en "Deploy" o mandá un mensaje de WhatsApp al +54 9 249 420-9659 para despertarlo.

---

## 3. Verificar que Paperclip está corriendo

```bash
curl http://localhost:3100/api/companies/31b28a68-67c6-4c2a-bb17-c92474870551/agents | head -c 200
```

Si no responde: Paperclip no está levantado.

```bash
# Arrancar Paperclip (buscá el directorio donde está instalado)
cd ~/Desktop/herramientas/paperclip && npm start
# o el comando que uses para levantarlo
```

---

## 4. Abrir Claude Code en el proyecto

Desde VS Code → Command Palette (`Cmd+Shift+P`) → "Claude: Open" → ya estás en contexto del proyecto `guiones`.

O desde terminal:

```bash
cd /Users/santiagofunes/Desktop/herramientas/inmobiliaria/guiones
claude
```

Claude Code lee automáticamente `CLAUDE.md` y tiene toda la memoria en `~/.claude/projects/`.

---

## 5. Qué está en la nube y qué no

| Sistema | Dónde vive | Qué pasa si se pierde la compu |
|---|---|---|
| **Código fuente** | GitHub → `santiagomfunes-crypto/dashboard-guiones` | ✅ Safe — clonar con `git clone` |
| **Sofía (bot)** | Railway → deployado en la nube | ✅ Safe — sigue funcionando sola |
| **Dashboard leads** | Vercel → `propiedades.santiagofunes.com.ar` | ✅ Safe — repo `sfre-web` en Vercel |
| **Base de datos** | Supabase (dos proyectos) | ✅ Safe — nube, no depende de la compu |
| **Agentes Paperclip** | `~/.paperclip/` en esta máquina | ⚠️ Riesgo — respaldar esta carpeta |
| **Variables Railway** | Railway dashboard | ✅ Safe — están cargadas en Railway |
| **Variables .env locales** | Solo en esta máquina | ⚠️ Riesgo — backup en `../backups/.env-guiones` |

---

## 6. Si perdés todo y tenés que empezar desde cero

### Paso 1 — Clonar el repo
```bash
cd ~/Desktop/herramientas/inmobiliaria
git clone https://github.com/santiagomfunes-crypto/dashboard-guiones.git guiones
```

### Paso 2 — Restaurar el .env
```bash
cp ../backups/.env-guiones guiones/.env
```

### Paso 3 — Credenciales clave (todas en Railway si te quedás sin .env)
| Variable | Dónde buscarla |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `WHATSAPP_TOKEN` | business.facebook.com → Usuarios del sistema → santi → Generar identificador |
| `SFRE_SUPABASE_URL` / `SERVICE_KEY` | supabase.com → proyecto `sfre-web` → Settings → API |
| `SUPABASE_URL` / `SERVICE_KEY` | supabase.com → proyecto `guiones` → Settings → API |

### Paso 4 — Instalar dependencias de scrapers
```bash
cd guiones && pip install -r railway-server/requirements.txt
```

---

## 7. Datos de acceso rápido (IDs importantes)

| Qué | ID / URL |
|---|---|
| Railway — Sofía bot | `https://sofia-bot-production-e17d.up.railway.app` |
| Dashboard leads | `https://propiedades.santiagofunes.com.ar/admin/leads` |
| Supabase guiones | `pgnmpxqljxrpnvexcygh.supabase.co` |
| Supabase sfre-web | `bsvcorcwcijpvwzxjzgu.supabase.co` |
| Meta App Sofía | App ID `948284884765195` |
| WhatsApp number | +54 9 249 420-9659 (Phone ID `1163990066789724`) |
| Business Manager | business.facebook.com → Business ID `122374272679098` |
| GitHub repo | `santiagomfunes-crypto/dashboard-guiones` |
| Paperclip company | `31b28a68-67c6-4c2a-bb17-c92474870551` |

---

## 8. ⚠️ Lo que SÍ está en riesgo si se va la compu

1. **`~/.paperclip/`** — configuración local de Paperclip. Si se pierde, hay que reconfigurar los adapters de los 13 agentes. Hacer backup periódico:
   ```bash
   cp -r ~/.paperclip ~/Desktop/herramientas/inmobiliaria/backups/paperclip-backup-$(date +%Y%m%d)
   ```

2. **`.env` local** — ya tiene backup en `../backups/.env-guiones`. Mantenerlo actualizado cuando cambie alguna variable.

3. **`~/.claude/`** — toda la memoria de Claude Code (30+ memories del proyecto). No tiene backup automático. Copiar periódicamente:
   ```bash
   cp -r ~/.claude ~/Desktop/herramientas/inmobiliaria/backups/claude-backup-$(date +%Y%m%d)
   ```

---

*Última actualización: 06/05/2026*
