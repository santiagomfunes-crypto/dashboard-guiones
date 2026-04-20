# Heartbeat — Agente SEO Writer

## 1. Wake-up check

- [ ] Leer tabla `reportes`: ¿cuándo corrí por última vez?
- [ ] Si fue hace menos de 6 días, no ejecutar.
- [ ] ¿Hay guiones nuevos con status="publicado" y rating>=3 que no convertí?

## 2. Seleccionar guiones a convertir

Query en Supabase:
```
tabla guiones
WHERE status = 'publicado'
AND rating >= 3
ORDER BY rating DESC, created_at DESC
LIMIT 5
```

De esos 5, elegir los 1-2 mejores según:
- Hook más fuerte (postura, dato, controversia)
- Tema con keyword de búsqueda real (crédito UVA, Tandil precios, alquilar vs comprar)
- Que no haya convertido ya en sesión anterior

Si no hay guiones publicados con rating>=3 → no ejecutar, reportar que falta contenido publicado.

## 3. Convertir cada guion a artículo

Para cada guion seleccionado, seguir la estructura del soul.md:

1. **Título SEO** (max 60 caracteres, incluye keyword)
2. **Intro** (100 palabras): el hook expandido
3. **Desarrollo** (600-800 palabras): datos del guion + datos adicionales de `referencia/datos-tandil.md` + contexto macro del último reporte del Macro Analyst
4. **Opinión de Santiago** (100-200 palabras): la postura del cierre expandida, en su voz
5. **Cierre**: resumen + pregunta que invite a comentar (NO CTA de venta)

Leer `referencia/voz-santiago.md` antes de escribir para mantener tono.

## 4. Guardar artículos

Guardar cada artículo en `referencia/articulos/` con nombre:
`articulo-[slug-titulo]-[fecha].md`

Si la carpeta no existe, crearla.

## 5. Reportar en Supabase (tabla `reportes`)

| Campo | Qué poner |
|---|---|
| `titulo` | "SEO Writer: X artículo(s) generado(s) — [dd/mm/aaaa]" |
| `agente` | "SEO Writer" |
| `contenido` | Lista de artículos generados con título, keyword objetivo y path del archivo |

## Frecuencia

Semanal (miércoles — después de que el Escritor haya corrido y haya guiones frescos).
