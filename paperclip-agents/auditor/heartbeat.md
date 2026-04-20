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
