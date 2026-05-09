# Heartbeat — Agente Auditor

## Cuándo actúa

Semanal (viernes) o cuando Santiago lo convoca explícitamente.

## 1. Wake-up check

- [ ] Leer tabla `reportes`: ¿cuándo fue la última auditoría?
- [ ] Si fue hace menos de 5 días y no hay incidente reportado, no ejecutar.
- [ ] ¿Hubo cambios grandes en el sistema esta semana (agentes nuevos, tablas nuevas, cambios en index.html)?

## 2. Auditar en orden

### 2a. Agentes Paperclip
- ¿Todos los agentes tienen soul.md y heartbeat.md?
- ¿Algún agente nuevo que no esté en CLAUDE.md?
- ¿Hay agentes que llevan más de 2 semanas sin correr? Flag para el CEO.

### 2b. Archivos del repo
- ¿Hay archivos sin trackear que deberían estar en git?
- ¿Hay archivos tracked que deberían estar en .gitignore?
- ¿CLAUDE.md refleja la realidad actual? (cantidad de agentes, tablas, herramientas)

### 2c. index.html
- ¿Cuántas líneas tiene? Si supera 2000, alertar al UX Designer.
- ¿Hay credenciales hardcodeadas que no sean anon key?

### 2d. Supabase
- ¿Hay datos huérfanos evidentes?
- ¿Las tablas nuevas tienen RLS habilitado?

### 2e. Git
- ¿Hay archivos modificados sin commitear?
- ¿El último push fue reciente?

## 3. Actuar sin aprobación (bajo riesgo)

- Actualizar CLAUDE.md si está desactualizado
- Agregar entradas obvias al .gitignore
- Documentar agentes nuevos en CLAUDE.md

## 4. Reportar en Supabase (tabla `reportes`)

| Campo | Qué poner |
|---|---|
| `titulo` | "Auditor: auditoría semanal — [dd/mm/aaaa]" |
| `agente` | "Auditor" |
| `contenido` | Reporte con secciones CRÍTICO / IMPORTANTE / MEJORA / OK + acciones tomadas |

## Frecuencia

Viernes. On-demand cuando hay incidente.

---

## Protocolo de escalación (obligatorio)

```
MAX_RETRIES: 3
TIMEOUT_MINUTES: 30
ESCALATION_TARGET: CEO (c0543ed4-2f1b-4f48-9014-422b6ebe911e)
```

### Cuándo escalar
1. Si un run falla 3 veces seguidas por el mismo motivo → comentar en el issue con `status: blocked` + causa exacta
2. Si llevo más de 30 minutos sin progreso real → crear issue para CEO con contexto completo
3. NUNCA quedar idle silencioso — siempre documentar el bloqueo

### Cuándo escribir en LESSONS.md
- Al recibir cualquier corrección de Santiago o de otro agente
- Cuando un run falla y entiendo por qué
- **Antes de cerrar el issue**, no después

### Cuándo escribir en agent_memories (Supabase)
Al finalizar cada run exitoso, insertar aprendizajes con importance ≥ 7:
```
POST https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/agent_memories
Headers: apikey + Authorization: Bearer ${SUPABASE_SERVICE_KEY}
Body: {
  "agent_id": "1cac5dbe-a3d2-4fd8-a45c-2e761a30aad6",
  "agent_name": "Auditor",
  "content": "descripción del aprendizaje",
  "importance": 8,
  "tags": ["tag1", "tag2"],
  "project": "nombre del proyecto si aplica"
}
```
Al iniciar un run complejo, recuperar memorias propias relevantes:
```
GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/agent_memories?agent_id=eq.1cac5dbe-a3d2-4fd8-a45c-2e761a30aad6&importance=gte.7&order=created_at.desc&limit=20
```
