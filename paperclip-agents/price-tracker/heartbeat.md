# Heartbeat — Agente Price Tracker

## 1. Wake-up check

- [ ] Leer tabla `reportes`: ¿cuándo corrí por última vez?
- [ ] Si fue hace menos de 6 días, no ejecutar salvo alerta.
- [ ] ¿Hubo noticias de cambios bruscos de precios en Tandil o CABA esta semana?

## 2. Buscar precios actualizados

### Tandil (prioridad máxima)
1. Buscar en Zonaprop "departamentos en venta Tandil" — anotar precio promedio publicado y rango
2. Buscar en Zonaprop "alquiler departamento Tandil" — 1 amb, 2 amb, 3 amb
3. Buscar en MercadoLibre Inmuebles "Tandil venta" — confirmar o contradecir Zonaprop
4. Buscar en Enfoque de Negocios o ABCHoy noticias de precios locales recientes
5. Si hay diferencia notable vs baseline del soul.md → anotar y flag como cambio significativo

### CABA (referencia)
1. Buscar dato m² CABA actualizado — Reporte Inmobiliario, Ámbito, Infobae Propiedades
2. Solo anotar si cambió vs baseline (USD 2.455/m²)

### CAC (costo construcción)
1. Buscar el CAC del último mes disponible — Cámara Argentina de la Construcción
2. Calcular variación acumulada vs baseline (+118% USD desde oct 2023)

## 3. Detectar cambios significativos

Un cambio es significativo si:
- M² Tandil varía >5% vs baseline (USD 2.000–2.600)
- Alquiler varía >10% vs baseline ($400.000/mes para 2 amb)
- CAC sube >3% mensual

Si hay cambio significativo: insertar en `newsletter` con hook propuesto.

## 4. Actualizar referencia

Actualizar `referencia/datos-tandil.md` sección de precios con fecha y fuente:

```
### Precios (referencia) — [MES AÑO]
- M² Tandil zona activa: USD X.XXX–X.XXX (fuente, fecha)
- M² Tandil zona premium (centro/4 avenidas): USD X.XXX+ (fuente)
- Depto 2 amb: USD XX.000–XX.000
- Alquiler 2 amb: $XXX.000–$XXX.000/mes
- M² CABA promedio: USD X.XXX (fuente)
- CAC acumulado vs oct 2023: +XXX% en USD
```

## 5. Reportar en Supabase (tabla `reportes`)

| Campo | Qué poner |
|---|---|
| `titulo` | "Price Tracker: precios [dd/mm/aaaa]" |
| `agente` | "Price Tracker" |
| `contenido` | Tabla de precios actualizados + cambios detectados + fuentes |

## Frecuencia

Semanal (lunes junto al Macro Analyst).

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
  "agent_id": "6e36fdd1-f221-42f4-b645-434db2169e2e",
  "agent_name": "Price Tracker",
  "content": "descripción del aprendizaje",
  "importance": 8,
  "tags": ["tag1", "tag2"],
  "project": "nombre del proyecto si aplica"
}
```
Al iniciar un run complejo, recuperar memorias propias relevantes:
```
GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/agent_memories?agent_id=eq.6e36fdd1-f221-42f4-b645-434db2169e2e&importance=gte.7&order=created_at.desc&limit=20
```
