# Guiones SFRE

Sistema de contenido para Santiago Funes Real Estate. Dashboard + agentes IA + base de datos en la nube.

## REGLAS CRÍTICAS — LEER ANTES DE HACER CUALQUIER COSA

### 1. Patrón de trabajo — dispatcher único

**Claude Code es dispatcher, no ejecutor.**

```
Santiago habla con Claude Code
        ↓
Claude Code crea issue en Paperclip (con descripción precisa)
        ↓
CEO de Paperclip decide y asigna
        ↓
Agentes ejecutan
        ↓
Claude Code verifica resultado si Santiago lo pide
```

**Claude Code PUEDE hacer directamente:**
- Configurar agentes, routines, skills, budgets en Paperclip via API (infraestructura del orquestador)
- Crear/despertar issues en Paperclip (rol de dispatcher)
- Discutir, diagnosticar, priorizar con Santiago

**Claude Code NO toca directamente:**
- `index.html` ni cualquier código del dashboard → UX Designer
- Guiones, variantes, hooks → Escritor
- Scrapers, scripts de datos → Arquitecto
- Soul files de agentes → CEO (los agentes se autoeditan)
- Cualquier artefacto del negocio en Supabase

**Si hay una urgencia real bloqueante** (Paperclip caído, bug crítico que impide trabajar): documentar el cambio como SAN-XXX en Paperclip con el commit, dejar constancia, y el agente responsable toma ownership en el próximo ciclo.

### 2. Crear issues en Paperclip así:
```
POST http://localhost:3100/api/companies/31b28a68-67c6-4c2a-bb17-c92474870551/issues
{ "title": "...", "description": "...", "assigneeAgentId": "CEO_ID" }
```
CEO ID: `c0543ed4-2f1b-4f48-9014-422b6ebe911e`
Despertar agente: `POST http://localhost:3100/api/agents/{id}/wakeup` con body `{"issueId": "uuid"}`

### 3. IDs de agentes Paperclip
CEO `c0543ed4` · Investigador `33ccac15` · Escritor `cc38b20a` · Analista `0128b9ab` · UX Designer `e38f08d1` · Macro Analyst `10936ff6` · Price Tracker `92b41890` · ROI Calculator `5a79f9aa` · SEO Writer `c40d6d8b` · Brain `1d118a87` · Auditor `1cac5dbe` · CMO `272499de`

## Arquitectura

- **Dashboard**: [index.html](index.html) — single-file HTML deployado en GitHub Pages (`santiagomfunes-crypto.github.io/dashboard-guiones/`)
- **Base de datos**: Supabase (tablas: guiones, variantes, newsletter, ideas, publicaciones, sesiones)
- **Agentes IA**: Paperclip con 14 agentes (soul files en `paperclip-agents/`)
- **Conocimiento**: `referencia/` (playbook, voz, datos, framework) + `youtube_brain/` (fuentes aprendidas)

## Credenciales

Viven en `.env` (gitignored) y en backup fuera del repo (`../backups/.env-guiones`). Supabase URL: `https://pgnmpxqljxrpnvexcygh.supabase.co`

## Usuarios del dashboard

- Santiago: santiagomfunes@gmail.com
- Celina: celina.colombo15@gmail.com
- Marcos: huergomarcos@gmail.com
- Password: santiago (todos)

## Estructura de carpetas

```
guiones/
├── index.html              ← dashboard (GitHub Pages)
├── supabase.min.js         ← SDK de Supabase (local, no CDN)
├── .gitignore
├── CLAUDE.md               ← este archivo
├── PARA-MARCOS.md          ← resumen para Marcos
├── contexto/               ← info del negocio y personal
├── referencia/             ← playbook, voz, datos, framework
├── paperclip-agents/       ← soul + heartbeat de cada agente
└── youtube_brain/          ← sistema de aprendizaje de fuentes
```

## Agentes Paperclip (14 activos)

| Agente | Qué hace | Frecuencia |
|---|---|---|
| CEO | Dirección estratégica del sistema | On-demand |
| Arquitecto | Diseña y revisa arquitectura del sistema | On-demand |
| Investigador | Busca tendencias del mercado | Cada 48h |
| Escritor | Escribe guiones + variantes de hook | Cada 72h |
| Publisher | Prepara briefings de publicación | Diario |
| Brain | Aprende de videos/web | On-demand |
| Analista | Analiza mix de contenido | Semanal |
| Estratega | Define estrategia de contenido | On-demand |
| Price Tracker | Rastrea precios m² Tandil/CABA | Semanal |
| ROI Calculator | Calcula retorno de propiedades | On-demand |
| Macro Analyst | Resumen macro semanal | Semanal |
| SEO Writer | Convierte guiones en artículos | Semanal |
| UX Designer | Mejora el dashboard | On-demand |
| Auditor | Verifica estado del sistema completo | Semanal (viernes) |

## Backups

SQL y credenciales en `~/Desktop/herramientas/inmobiliaria/backups/` (fuera del repo).

## Para agregar un guion nuevo

Los guiones viven en Supabase, no en el HTML. Se agregan desde el dashboard o los genera el Escritor automáticamente.
