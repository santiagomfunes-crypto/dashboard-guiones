# Heartbeat — Agente UX Designer

## 1. Wake-up check

- [ ] ¿Hay issue asignado con pedido de mejora UX?
- [ ] ¿Hay feedback de Celina o Santiago sobre el dashboard? (revisar feedback.json si existe)
- [ ] ¿Los otros agentes hicieron cambios que requieren actualización de UI? (nuevas tablas, nuevos campos, nuevas vistas)

## 2. Decidir qué hacer

**Si hay issue asignado** → implementar la mejora pedida (prioridad 1).

**Si hay feedback de usuarios** → evaluar impacto y priorizar. Bugs > usabilidad > cosméticos.

**Si hay cambios en datos/estructura** → adaptar UI para reflejar los nuevos datos.

**Si no hay nada pendiente** → no tocar el dashboard. Reportar "sin pedidos".

## 3. Ejecutar

### 3a. Entender el cambio
1. Leer el index.html actual (o la sección relevante)
2. Identificar exactamente qué HTML/CSS/JS se modifica
3. Verificar que el cambio no conflictúa con funcionalidad existente

### 3b. Implementar
1. Editar index.html
2. Respetar identidad visual: Montserrat + Cinzel, Navy #1a1a2e + Gold #8B6F3A + Cream #F5F5F3
3. Mobile-first: verificar en 375px de ancho
4. Agregar feedback visual a cualquier interacción nueva
5. Mantener performance (no agregar peso innecesario)

### 3c. Testear
- [ ] ¿Funciona en mobile (375px)?
- [ ] ¿Funciona en desktop?
- [ ] ¿Los colores y tipografía son consistentes?
- [ ] ¿Las queries a Supabase siguen funcionando?
- [ ] ¿No se rompió nada existente?
- [ ] ¿Cada botón/acción tiene feedback visual?

### 3d. Deployar
```bash
git add index.html
git commit -m "dashboard: [descripción concisa]"
git push origin main
```
Verificar que el deploy a GitHub Pages se complete (tarda ~1 min).

## 4. Verificar calidad

- [ ] Abrir `santiagomfunes-crypto.github.io/dashboard-guiones/` en mobile
- [ ] Navegar todas las secciones afectadas
- [ ] Verificar que los datos de Supabase cargan correctamente
- [ ] Verificar que el diseño se ve profesional (Notion/Linear level, no prototipo)

## 5. Reportar

Dejar reporte con:
- Qué cambió en el dashboard (descripción concisa)
- Screenshots o descripción visual del antes/después
- Si el cambio afecta el flujo de otros agentes
- Si detectó otros problemas de UX durante la implementación

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
  "agent_id": "e38f08d1-dd44-42ea-8893-ac0aa7a1c2e4",
  "agent_name": "Ux Designer",
  "content": "descripción del aprendizaje",
  "importance": 8,
  "tags": ["tag1", "tag2"],
  "project": "nombre del proyecto si aplica"
}
```
Al iniciar un run complejo, recuperar memorias propias relevantes:
```
GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/agent_memories?agent_id=eq.e38f08d1-dd44-42ea-8893-ac0aa7a1c2e4&importance=gte.7&order=created_at.desc&limit=20
```
