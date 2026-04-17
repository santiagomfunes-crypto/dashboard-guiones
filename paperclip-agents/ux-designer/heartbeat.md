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
