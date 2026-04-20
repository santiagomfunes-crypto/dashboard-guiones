# Heartbeat — Agente Macro Analyst

## 1. Wake-up check

- [ ] Leer tabla `reportes` de Supabase: ¿cuándo fue el último reporte del Macro Analyst?
- [ ] Si fue hace menos de 5 días y no hay cambio macro urgente, no ejecutar.
- [ ] Si IPC, dólar o tasas hipotecarias cambiaron bruscamente esta semana → ejecutar aunque no hayan pasado 7 días.

## 2. Recolectar indicadores

En este orden:

1. **IPC último mes** — INDEC (indec.gob.ar) o Infobae Economía
2. **Dólar oficial + MEP + blue** — ambito.com o dolarhoy.com
3. **UVA actualizada** — BCRA (bcra.gob.ar)
4. **Tasas hipotecarias** — ¿algún banco cambió tasa esta semana? buscar en infobae, creditosuva.ar
5. **Escrituras CABA** — Colegio de Escribanos (si hay dato nuevo del mes anterior)
6. **CAC** — si salió dato nuevo mensual

Para cada indicador: anotar valor actual + valor anterior + variación + fuente + fecha.

## 3. Detectar alertas

¿Alguno de estos disparadores?

- IPC sube más de 1 punto vs mes anterior → alerta urgente
- Banco importante cambia tasa hipotecaria → alerta urgente
- Dólar blue se mueve más de 5% en la semana → alerta
- BCRA cambia tasa de política monetaria → alerta urgente

Si hay alerta: insertar en `newsletter` con prioridad alta y angulo="pred" o "prob".

## 4. Armar reporte macro

Usar el formato del soul.md:

```
MACRO SEMANAL — [fecha]

LO MÁS IMPORTANTE: [1 línea con el dato clave]

INDICADORES:
- IPC: X,X% (vs X,X% mes anterior) [tendencia: sube/baja/estable]
- Dólar: $X.XXX oficial / $X.XXX MEP / $X.XXX blue
- UVA: $X.XXX [variación mensual]
- Tasas hipotecarias: sin cambios / [banco] modificó a X%

IMPLICANCIA PARA REAL ESTATE:
[2-3 líneas sobre qué significa esto para comprar/vender/invertir]

HOOK SUGERIDO PARA GUION:
"[hook en voz de Santiago — rioplatense, dato conversacional, postura fuerte]"
```

## 5. Insertar en newsletter

Si hay dato nuevo relevante (no repetir lo que ya está):
- Insertar en tabla `newsletter` con todos los campos completos
- angulo: prob / pred / comp según el dato
- hook_propuesto en voz de Santiago

## 6. Actualizar referencia

Actualizar sección "Mercado Nacional" de `referencia/datos-tandil.md` con los valores frescos.

## 7. Reportar en Supabase (tabla `reportes`)

Insertar al terminar:

| Campo | Qué poner |
|---|---|
| `titulo` | "Macro Analyst: resumen semanal — [dd/mm/aaaa]" |
| `agente` | "Macro Analyst" |
| `contenido` | El reporte completo del paso 4 + cantidad de entradas insertadas en newsletter |

## Frecuencia

Semanal (lunes). Alerta inmediata si hay cambio brusco.
