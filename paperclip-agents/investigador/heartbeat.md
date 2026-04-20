# Heartbeat — Agente Investigador

## 1. Wake-up check

- [ ] Leer tabla `newsletter` de Supabase: cuántas entradas hay, cuándo fue la última
- [ ] Si la última entrada fue hace menos de 2 días, evaluar si hay noticias urgentes que justifiquen buscar antes
- [ ] Revisar si hay issues asignados con pedidos específicos de investigación
- [ ] **Leer el último reporte del Analista en tabla `reportes`** (agente='Analista'): ¿qué ángulos están sub-representados? ¿qué temas recomienda reforzar? Priorizar búsquedas en base a eso.

## 2. Decidir qué hacer

**Si hay issue asignado** → investigar el tema específico del issue.

**Si no hay issue pero pasaron 2+ días desde la última entrada** → buscar tendencias generales.

**Si hay ángulos sub-representados** → priorizar búsquedas que llenen esos huecos.

**Si la última entrada fue hace <2 días y no hay issues** → no ejecutar. Reportar "sin novedades".

## 3. Ejecutar búsqueda

### 3a. Buscar noticias (en este orden)
1. Tasas hipotecarias: ¿algún banco cambió tasa esta semana?
2. INDEC / BCRA: ¿salió dato nuevo de IPC, empleo, crédito?
3. Escrituras CABA: ¿hay dato mensual nuevo?
4. Tandil específico: ¿noticia local de desarrollo, turismo, urbanismo?
5. Temas adyacentes: ¿algo viral en finanzas personales, impuestos, decisiones de vida?

### 3b. Para cada hallazgo potencial, filtrar
- [ ] ¿El dato es NUEVO? (no está ya en tabla newsletter ni en datos quemados)
- [ ] ¿Tiene dato duro? (sin número = descartar)
- [ ] ¿Conecta con alguno de los 8 ángulos PPOS+?
- [ ] ¿Santiago podría hacer 60 segundos sobre esto?
- [ ] ¿Es específico, no genérico?
- [ ] ¿Prioriza educación/opinión sobre producto? (ratio 90/10)

### 3c. Armar propuestas
Para cada hallazgo que pase el filtro:
1. Elegir ángulo PPOS+
2. Extraer dato duro principal
3. Escribir hook propuesto en voz de Santiago (rioplatense, dato conversacional, postura fuerte, sin preguntas retóricas)
4. Escribir `por_que_pega` en 1 línea
5. Guardar fuente_url

## 4. Verificar calidad

Antes de insertar, para CADA propuesta:

- [ ] ¿El hook suena a Santiago o suena a nota de prensa?
- [ ] ¿El dato es verificable con la fuente?
- [ ] ¿No estoy repitiendo un dato quemado? (Josefina/35 edificios/5,8 mudanzas/20,5% crecimiento/10K viviendas/30% alquila)
- [ ] ¿No estoy repitiendo una entrada anterior de newsletter?
- [ ] ¿El ángulo elegido es correcto o hay uno mejor?

## 5. Insertar en Supabase

Insertar cada propuesta en tabla `newsletter` con todos los campos completos.

## 6. Reportar en Supabase (tabla `reportes`)

Al terminar, insertar un registro en la tabla `reportes` de Supabase con:

| Campo | Qué poner |
|---|---|
| `titulo` | "Investigador: X propuestas nuevas — [dd/mm/aaaa]" |
| `agente` | "Investigador" |
| `contenido` | Texto completo del reporte (ver formato abajo) |

### Formato del campo `contenido`

```
PROPUESTAS INSERTADAS: X

1. [título] — ángulo: [ángulo] — dato: [dato_duro]
2. [título] — ángulo: [ángulo] — dato: [dato_duro]
...

TEMAS QUE BUSQUÉ Y NO ENCONTRÉ:
- [tema]: [razón por la que no avancé]

SEGUIMIENTO SUGERIDO:
- [tema caliente que merece vigilancia en próximos días]

ACCIÓN REQUERIDA:
Revisar propuestas en tab Newsletter del dashboard y aprobar las que procedan para que el Escritor las convierta en guiones.
```

Este reporte aparece automáticamente en el tab **Reportes** del dashboard. Santiago lo ve ahí sin necesidad de preguntar.
