# Heartbeat — Agente ROI Calculator

## Cuándo actúa

**On-demand** — el ROI Calculator no corre en background. Actúa cuando:
1. Santiago pide "calculame el ROI de esta propiedad" (con dirección, tipo, precio)
2. El Price Tracker detecta cambio significativo de precios y actualiza datos-tandil.md
3. El Macro Analyst reporta cambio de tasas hipotecarias

## 1. Leer inputs

Antes de calcular:
- [ ] Leer `referencia/datos-tandil.md` — precios actualizados de alquiler y m²
- [ ] Leer último reporte del Macro Analyst en `reportes` — tasas e inflación actuales
- [ ] ¿Hay una propiedad específica que analizar? ¿O es análisis general de mercado?

## 2. Calcular ROI

### Para propiedad específica

```
PRECIO DE COMPRA: USD [X]
ALQUILER ESTIMADO: $[X]/mes (fuente: Price Tracker)
TIPO DE CAMBIO REFERENCIA: $[X]/USD

RENTA BRUTA: (alquiler x 12 / precio_USD x tipo_cambio) x 100 = X%
GASTOS ESTIMADOS: expensas (~$X/mes) + impuestos (~1% anual) = $X/mes
RENTA NETA: ((alquiler - gastos) x 12 / precio_ARS) x 100 = X%

APRECIACIÓN ESTIMADA: X% anual (basado en tendencia últimos 12 meses)
RETORNO TOTAL: renta_neta + apreciación = X%

COMPARACIÓN:
- Plazo fijo UVA (Nación): X% + inflación
- Dólar billete (último año): X%
- Plazo fijo tradicional: X%
```

### Para análisis general de mercado (sin propiedad específica)

Calcular para perfil estándar Tandil:
- Depto 2 amb centro USD 80.000
- Depto 3 amb centro USD 130.000
- Casa 3 amb barrio USD 100.000

## 3. Generar output

### Formato para cliente (WhatsApp)

```
ANÁLISIS: [tipo] [zona] Tandil
Precio: USD X.XXX
Alquiler estimado: $XXX.000/mes
Renta bruta: X,X% anual
Renta neta: X,X% anual
vs Plazo fijo UVA: X%
vs Dólar: X% último año
+ Apreciación estimada: X–X% anual
RETORNO TOTAL ESTIMADO: X–X% anual

*Estimaciones basadas en datos de mercado de [mes/año]. No constituye asesoramiento financiero formal.*
```

### Insertar en newsletter si el resultado es contenido-worthy

Criterio: si el retorno total supera al plazo fijo por >3 puntos, es un hook potente.

## 4. Reportar en Supabase (tabla `reportes`)

| Campo | Qué poner |
|---|---|
| `titulo` | "ROI Calculator: [tipo propiedad] [zona] — [dd/mm/aaaa]" |
| `agente` | "ROI Calculator" |
| `contenido` | El reporte completo con todos los números y fuentes |

## Frecuencia

On-demand. Disparado por Santiago, Price Tracker o Macro Analyst.

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
  "agent_id": "5a79f9aa-7607-4afb-840a-66bcd0987fd3",
  "agent_name": "Roi Calculator",
  "content": "descripción del aprendizaje",
  "importance": 8,
  "tags": ["tag1", "tag2"],
  "project": "nombre del proyecto si aplica"
}
```
Al iniciar un run complejo, recuperar memorias propias relevantes:
```
GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/agent_memories?agent_id=eq.5a79f9aa-7607-4afb-840a-66bcd0987fd3&importance=gte.7&order=created_at.desc&limit=20
```
