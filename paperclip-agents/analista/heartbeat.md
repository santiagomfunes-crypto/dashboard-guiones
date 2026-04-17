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

## 5. Reportar

Formato del reporte semanal:

```
## Distribución actual vs. objetivo
| Ángulo | Actual | Target | Delta |
|--------|--------|--------|-------|
| ...    | ...    | ...    | ...   |

## Huecos a llenar (top 3)
1. ...
2. ...
3. ...

## Para filmar esta semana (top 3)
1. [título] — ángulo X, formato Y — justificación
2. ...
3. ...

## Recomendaciones
- Investigador: buscar temas de [ángulo] sobre [tema]
- Escritor: priorizar [formato] con ángulo [X]
```

Dejar como comentario en el issue o como reporte standalone.
