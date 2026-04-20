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
