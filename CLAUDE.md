# Guiones SFRE — Claude Code Dispatch Manual

Sistema de contenido para Santiago Funes Real Estate. Dashboard + 13 agentes IA + Supabase.

## AGENTE OJOS — Browser automation

`agent-browser` v0.26.0 está instalado globalmente. Cuando Santiago diga "usa el agente ojos" o "scrapeá con el browser", usar directamente desde Claude Code:

```bash
# Ver página como la ve un agente IA
agent-browser open <url> snapshot --json

# Extraer texto
agent-browser open <url> text --json

# Interactuar (click, fill, etc.)
agent-browser open <url> click "@e1" --json
```

Flujo estándar para scraping: `open` → `snapshot` (obtener refs @e1, @e2...) → interactuar o extraer. Usar `--json` siempre para output limpio. Chrome instalado en `~/.agent-browser/browsers/chrome-148.0.7778.97`.

---

## ⚠️ REGLA MÁXIMA — LEER ANTES DE CUALQUIER COSA

**Criterio de routing — antes de cada tarea, elegir el canal correcto:**

| Canal | Cuándo usarlo |
|---|---|
| **Claude Code directamente** | Pedidos on-demand en el chat: copy, tasaciones, consultas, análisis rápidos, cualquier cosa que Santiago necesita ahora |
| **Paperclip** | Rutinas automáticas (scraping, reportes semanales), tareas largas que corren solas, cosas que no requieren atención inmediata de Santiago |

Paperclip no es más rápido que Claude Code para pedidos en el chat. Su valor es la autonomía y la ejecución sin supervisión.

---

## ROL DE CLAUDE CODE: DISPATCHER, NO EJECUTOR

```
Santiago habla con Claude Code
        ↓
¿Es on-demand / necesita respuesta inmediata?
    SÍ → Claude Code ejecuta directamente
    NO → Claude Code crea issue en Paperclip → agentes ejecutan solos
```

**Claude Code PUEDE hacer directamente:**
- Configurar infraestructura de Paperclip: agentes, routines, skills, budgets (via API)
- Crear/despertar issues (rol de dispatcher)
- Diagnosticar, priorizar, discutir con Santiago
- Tareas on-demand: copy, análisis, tasaciones, consultas

**Claude Code NO toca:**
- `index.html` ni dashboard → UX Designer
- Guiones, variantes, hooks → Escritor
- Scrapers, scripts de datos → Arquitecto
- Artefactos del negocio en Supabase (guiones, newsletter, propiedades)

**Excepción bloqueante:** si Paperclip está caído o hay un bug crítico que impide trabajar, documentar el cambio como SAN-XXX y dejar constancia para que el agente responsable tome ownership.

---

## REGLAS CRÍTICAS PAPERCLIP (errores que NO se repiten)

### Issues — SIEMPRE así:
```json
POST http://localhost:3100/api/companies/31b28a68-67c6-4c2a-bb17-c92474870551/issues
{
  "title": "Agente: descripción accionable",
  "description": "Contexto detallado",
  "status": "todo",
  "priority": "medium",
  "assigneeAgentId": "uuid",
  "goalId": "uuid",
  "projectId": "uuid"
}
```
- ❌ NUNCA `status: "backlog"` — los agentes solo buscan `todo,in_progress,blocked`
- ❌ NUNCA sin `goalId` — sin él el agente no tiene trazabilidad estratégica
- ❌ NUNCA sin `projectId` — sin él el issue queda huérfano

### Routines — crear con trigger inline en una sola llamada:
```json
POST http://localhost:3100/api/companies/31b28a68-67c6-4c2a-bb17-c92474870551/routines
{
  "title": "Agente: tarea recurrente",
  "assigneeAgentId": "uuid",
  "projectId": "uuid",
  "status": "active",
  "concurrencyPolicy": "skip_if_active",
  "catchUpPolicy": "skip_missed",
  "triggers": [{
    "kind": "schedule",
    "label": "Descripción legible",
    "enabled": true,
    "cronExpression": "0 9 * * 1",
    "timezone": "America/Argentina/Buenos_Aires"
  }]
}
```
- ❌ NUNCA `enabled: false` en triggers — la routine queda inerte
- Si se necesita agregar trigger después: `POST /api/routines/{id}/triggers`
- Para editar routine existente: `PATCH /api/routines/{id}` (sin company prefix)

### Despertar agente manualmente:
```bash
POST http://localhost:3100/api/agents/{agentId}/heartbeat/invoke
Body: { "issueId": "uuid-completo-del-issue" }
```
- ❌ NUNCA `/wakeup` — devuelve 403
- ❌ NUNCA construir UUIDs manualmente — usar SIEMPRE el `id` exacto que devuelve la API al crear el issue

### Agente nuevo — checklist obligatorio antes de poner en producción:
- [ ] Crear agente via API → guardar el `id` exacto que devuelve
- [ ] Crear carpeta `instructions/` dentro del directorio del agente
- [ ] SOUL.md, HEARTBEAT.md, AGENTS.md dentro de `instructions/`
- [ ] PATCH del agente con `adapterType: "claude_local"` y `adapterConfig` completo (ver Arquitecto como modelo)
- [ ] Routine con trigger `enabled: true` (si no es on-demand)
- [ ] Crear issue de prueba con `status: "todo"`, `goalId`, `projectId` → guardar su `id` exacto
- [ ] Despertar con `/heartbeat/invoke` usando el `id` exacto del issue
- [ ] Verificar que el agente pasa a `running` dentro de 30 segundos

---

## IDs SFRE

### Agentes (org chart):
```
CEO          c0543ed4-2f1b-4f48-9014-422b6ebe911e
├── CMO      272499de-2fd3-4e00-bb38-89c76b664bf7
│   ├── Investigador  33ccac15-166f-4a93-8ec1-3cc939911c18
│   ├── Escritor      cc38b20a-207a-43ff-8afd-d226cd721771
│   ├── Analista      0128b9ab-1387-4a8c-99fb-3d5edf267f09
│   ├── Brain         1d118a87-3637-40c5-a967-e25bbbbda204
│   └── SEO Writer    c40d6d8b-483f-46bf-8feb-13cd8ae5e778
├── Price Tracker     6e36fdd1-f221-42f4-b645-434db2169e2e  ← agente nuevo (92b41890 terminado)
├── Macro Analyst     10936ff6-8f2e-4d68-86b1-a186bd2df166
├── ROI Calculator    5a79f9aa-7607-4afb-840a-66bcd0987fd3
├── Tasador           1d36e643-6846-49c9-a3d2-095dafc02786
├── UX Designer       e38f08d1-dd44-42ea-8893-ac0aa7a1c2e4
├── Arquitecto        811a223b-b1fe-4693-9851-89c4d04ee23b
└── Auditor           1cac5dbe-a3d2-4fd8-a45c-2e761a30aad6
```

### Goals (contexto estratégico de cada issue):
```
Goal Marca Personal:    f2d0a842-ee6a-4ca5-b1f3-0280a5c046b9
Goal Máquina Contenido: f151a335-b719-4762-8f6d-79a785d66523
```

### Projects (agrupación operativa):
```
Producción de Contenido: 7e44aab2-0291-41cd-8af7-403e90c0683a
Inteligencia de Mercado: 44e8c697-3645-4f09-b6e7-7169795794ba
Dashboard & Plataforma:  4685aaa8-f0bf-4ea2-af0d-bb43eeba3e15
Cadencia Operativa:      003d7211-f95a-43e4-a0ec-9bd1456c5c0d
```

---

## SCHEDULES (routines activas)

| Agente | Cron | Horario BA |
|---|---|---|
| CMO | `0 13 * * *` | 10AM todos los días |
| Investigador | `0 11 * * 1,4` | 8AM lunes y jueves |
| Escritor | `0 9 * * 3` | 6AM miércoles |
| Macro Analyst | `0 9 * * 1` | 6AM lunes |
| Analista | `0 9 * * 5` | 6AM viernes |
| SEO Writer | `0 9 * * 3` | 6AM miércoles |
| Price Tracker | `0 9 * * 1` | 6AM lunes |
| Auditor | `0 21 * * 5` | 6PM viernes |
| Arquitecto | `30 9 * * *` | 6:30AM diario (scraper CasasDeHoy) |
| Arquitecto | `0 6 * * *` | 3AM diario (scraper MercadoLibre) |

---

## FLUJO QA LOOP (obligatorio para guiones)

```
Escritor escribe guion → Supabase status='en_revision'
        ↓
Escritor crea issue para CMO: "CMO: QA guion — [título]"
        ↓
CMO evalúa los 6 criterios
├── Aprueba → PATCH guion status='listo'
└── Rechaza → crea issue para Escritor con feedback específico
```

---

## ARQUITECTURA

- **Dashboard**: `index.html` — GitHub Pages (`santiagomfunes-crypto.github.io/dashboard-guiones/`)
- **Base de datos**: Supabase `https://pgnmpxqljxrpnvexcygh.supabase.co`
  - Tablas: `guiones`, `variantes`, `newsletter`, `ideas`, `publicaciones`, `sesiones`, `reportes`, `propiedades_mercado`, `agent_memories`
  - `agent_memories`: memoria persistente cross-agente. Campos: `agent_id`, `agent_name`, `content`, `importance (1-10)`, `tags[]`, `project`, `superseded_by`. Los agentes escriben aprendizajes con importance ≥ 7 al finalizar runs y leen al iniciar runs complejos.
- **Credenciales**: `.env` (gitignored) + backup en `../backups/.env-guiones`
- **Agentes**: soul files en `paperclip-agents/` + instructions en `~/.paperclip/instances/default/companies/.../agents/`
  - Cada agente tiene: `SOUL.md`, `HEARTBEAT.md`, `AGENTS.md`, `TOOLS.md`, `LESSONS.md` (nuevo)
  - `LESSONS.md`: registro de errores y correcciones. El agente lo actualiza antes de cerrar cualquier issue fallido.
- **Conocimiento**: `referencia/` (playbook, voz, datos, framework) + `youtube_brain/`

## Usuarios del dashboard
- Santiago: santiagomfunes@gmail.com | Celina: celina.colombo15@gmail.com | Marcos: huergomarcos@gmail.com
- Password: santiago (todos)

## Backups
SQL y credenciales en `~/Desktop/herramientas/inmobiliaria/backups/`
