# Heartbeat — Agente Analista

## 1. Wake-up check

- [ ] ¿Hay issue asignado pidiendo análisis específico?
- [ ] ¿Cuándo fue mi último reporte? Si fue hace menos de 5 días y no hay issue, no ejecutar.
- [ ] ¿Hubo cambios significativos en las tablas desde el último reporte? (guiones nuevos, newsletter nuevas)

## 2. Decidir qué hacer

**Si hay issue asignado** → análisis específico pedido.

**Si pasaron 7+ días desde el último reporte** → análisis semanal completo.

**Si hubo muchos cambios (5+ guiones nuevos)** → análisis de impacto.

**Si no hay cambios significativos y el último reporte fue reciente** → no ejecutar.

## 3. Ejecutar análisis

### 3a. Recolectar datos
1. Query tabla `guiones`: count por angulo, count por tema, count por status, count por tipo
2. Query tabla `newsletter`: count de entradas con convertido=false
3. Query tabla `ideas`: count por estado

### 3b. Calcular distribución vs. target
Para cada ángulo:
```
actual_pct = count_angulo / total_guiones * 100
delta = actual_pct - target_pct
status = "OK" si |delta| < 3, "FALTA" si delta < -3, "EXCESO" si delta > 5
```

Targets: prob=16, prod=10, sol=14, con=16, aut=14, hist=16, pred=8, comp=6

### 3c. Identificar huecos
1. Ángulos con mayor delta negativo → top huecos
2. Temas que no aparecen en los últimos 20 guiones
3. Formatos Briones que no se usaron en los últimos 10 guiones
4. Entradas de newsletter potentes que no se convirtieron

### 3d. Seleccionar top guiones para filmar
Del pool con status="listo":
1. Filtrar los que tienen datos frescos (<2 semanas)
2. Priorizar ángulos sub-representados
3. Verificar variedad temática (no 3 del mismo tema)
4. Elegir top 3 con justificación de 1 línea cada uno

## 4. Verificar calidad del reporte

- [ ] ¿La tabla de distribución es precisa? (los % suman ~100)
- [ ] ¿Los huecos identificados son accionables? (el Escritor puede hacer algo con esto)
- [ ] ¿Los guiones recomendados para filmar están realmente en status "listo"?
- [ ] ¿El reporte cabe en una pantalla? (si no, recortar)

## 5. Reportar en Supabase (tabla `reportes`)

Insertar al terminar:

| Campo | Qué poner |
|---|---|
| `titulo` | "Analista: distribución semanal — [dd/mm/aaaa]" |
| `agente` | "Analista" |
| `contenido` | El reporte completo con formato abajo |

Formato del campo `contenido`:

```
DISTRIBUCIÓN ACTUAL VS. OBJETIVO
| Ángulo | Actual | Target | Delta | Status |
|--------|--------|--------|-------|--------|
| ...    | ...    | ...    | ...   | ...    |

HUECOS A LLENAR (top 3)
1. ...
2. ...
3. ...

PARA FILMAR ESTA SEMANA (top 3)
1. [título] — ángulo X, formato Y — justificación
2. ...
3. ...

RECOMENDACIONES
- Investigador: buscar temas de [ángulo] sobre [tema]
- Escritor: priorizar [formato] con ángulo [X]
```

Este reporte queda visible en el tab Reportes del dashboard y el Investigador lo lee en su próximo wake-up.

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
  "agent_id": "0128b9ab-1387-4a8c-99fb-3d5edf267f09",
  "agent_name": "Analista",
  "content": "descripción del aprendizaje",
  "importance": 8,
  "tags": ["tag1", "tag2"],
  "project": "nombre del proyecto si aplica"
}
```
Al iniciar un run complejo, recuperar memorias propias relevantes:
```
GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/agent_memories?agent_id=eq.0128b9ab-1387-4a8c-99fb-3d5edf267f09&importance=gte.7&order=created_at.desc&limit=20
```
