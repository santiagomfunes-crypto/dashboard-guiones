# Heartbeat — Agente Brain

## 1. Wake-up check

- [ ] ¿Hay issues asignados con URLs para aprender?
- [ ] ¿Hay JSONs nuevos en `youtube_brain/brain_data/` sin destilar?
- [ ] ¿Hay 3+ fuentes sobre un mismo tema que no se destilaron en un archivo de referencia?
- [ ] ¿Algún archivo de `referencia/` tiene datos desactualizados? (check fechas de última actualización al final de cada archivo)

## 2. Decidir qué hacer

**Si hay issue con URL** → extraer y procesar la URL (prioridad 1).

**Si hay 3+ fuentes sin destilar** → crear o actualizar archivo de referencia.

**Si hay archivo desactualizado** → buscar si hay fuentes nuevas en brain_data que lo actualicen.

**Si no hay nada pendiente** → no ejecutar. Reportar "sin input".

## 3. Ejecutar

### 3a. Extraer contenido de URL
1. Identificar tipo: YouTube → usar brain.py; Web → usar requests+BeautifulSoup
2. Extraer contenido completo
3. Procesar en formato JSON: source, url, date, key_points, quotes, data_points, relevance_to_sfre
4. Guardar en `youtube_brain/brain_data/` con nombre descriptivo

### 3b. Destilar en archivo de referencia
1. Leer todas las fuentes sobre el tema (JSONs en brain_data/)
2. Leer el archivo de referencia actual (si existe)
3. Reescribir el archivo completo — NO agregar al final
4. Mantener sección de fuentes al pie con todas las fuentes (nuevas + anteriores)
5. Para cada dato: fuente inline o `[NO VERIFICADO]`
6. Destacar aplicaciones concretas para Santiago (hooks, datos "decibles", posturas posibles)

### 3c. Commitear cambios
```bash
git add referencia/<archivo>.md
git commit -m "brain: actualizar <archivo> con N fuentes nuevas"
```

## 4. Verificar calidad

- [ ] ¿El archivo destilado es más corto o igual que antes? (reescribir = sintetizar, no inflar)
- [ ] ¿Cada dato tiene fuente?
- [ ] ¿Los claims no verificables están marcados?
- [ ] ¿Hay al menos 2-3 "aplicaciones Santiago" concretas?
- [ ] ¿La sección de fuentes al pie lista TODAS las fuentes usadas?

## 5. Reportar

Dejar reporte con:
- Qué URL(s) procesó
- Qué archivo(s) de referencia actualizó o creó
- Key takeaways: 3-5 puntos principales que aprendió
- Aplicaciones para Santiago: qué hooks o ángulos nuevos surgieron
- Qué queda pendiente (fuentes que aún no llegan a 3 para destilar)
