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
  "agent_id": "1d118a87-3637-40c5-a967-e25bbbbda204",
  "agent_name": "Brain",
  "content": "descripción del aprendizaje",
  "importance": 8,
  "tags": ["tag1", "tag2"],
  "project": "nombre del proyecto si aplica"
}
```
Al iniciar un run complejo, recuperar memorias propias relevantes:
```
GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/agent_memories?agent_id=eq.1d118a87-3637-40c5-a967-e25bbbbda204&importance=gte.7&order=created_at.desc&limit=20
```
