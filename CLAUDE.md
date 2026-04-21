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

### 3. IDs de agentes Paperclip (org chart actual)

```
CEO          c0543ed4-2f1b-4f48-9014-422b6ebe911e
├── CMO      272499de-2fd3-4e00-bb38-89c76b664bf7
│   ├── Investigador  33ccac15-166f-4a93-8ec1-3cc939911c18
│   ├── Escritor      cc38b20a-207a-43ff-8afd-d226cd721771
│   ├── Analista      0128b9ab-1387-4a8c-99fb-3d5edf267f09
│   ├── Brain         1d118a87-3637-40c5-a967-e25bbbbda204
│   └── SEO Writer    c40d6d8b-483f-46bf-8feb-13cd8ae5e778
├── Price Tracker     92b41890-b60c-48fd-8100-1fc9896aed9f
├── Macro Analyst     10936ff6-8f2e-4d68-86b1-a186bd2df166
├── ROI Calculator    5a79f9aa-7607-4afb-840a-66bcd0987fd3
├── UX Designer       e38f08d1-dd44-42ea-8893-ac0aa7a1c2e4
├── Arquitecto        811a223b-b1fe-4693-9851-89c4d04ee23b
└── Auditor           1cac5dbe-a3d2-4fd8-a45c-2e761a30aad6
```

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

## Agentes Paperclip (13 activos)

| Agente | Qué hace | Frecuencia |
|---|---|---|
| CEO | Dirección estratégica, crea issues para el equipo | On-demand |
| CMO | Coordina equipo de contenido, QA de guiones | On-demand |
| Investigador | Tendencias del mercado → tabla newsletter | Cada 48h |
| Escritor | Guiones 200-350 palabras → Supabase | Cada 72h |
| Analista | Mix de ángulos PPOS+ vs targets | Semanal |
| Brain | Aprende de URLs externas, actualiza referencia/ | On-demand |
| SEO Writer | Guiones publicados → artículos SEO | Semanal |
| Price Tracker | Precios m² Tandil/CABA + CAC | Semanal |
| Macro Analyst | IPC, dólar, UVA, tasas hipotecarias | Semanal |
| ROI Calculator | Retorno de inversión on-demand | On-demand |
| UX Designer | Dashboard index.html (owner del código) | On-demand |
| Arquitecto | Sistemas técnicos (webs, agentes, integraciones) | On-demand |
| Auditor | Estado del sistema + patrón dispatcher | Semanal (viernes) |

## Backups

SQL y credenciales en `~/Desktop/herramientas/inmobiliaria/backups/` (fuera del repo).

## Para agregar un guion nuevo

Los guiones viven en Supabase, no en el HTML. Se agregan desde el dashboard o los genera el Escritor automáticamente.
