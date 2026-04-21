# Heartbeat — Agente CMO

## Cuándo actúa

On-demand. El CMO actúa cuando:
- El CEO le asigna un issue de coordinación
- El Escritor termina un guión y necesita revisión
- Hay una decisión de contenido semanal que tomar
- Un agente del equipo está bloqueado o inactivo

## 1. Wake-up check

- [ ] Revisar inbox: ¿hay issues asignados al CMO?
- [ ] ¿El Escritor tiene guiones pendientes de revisión (`status: borrador`)?
- [ ] ¿El Investigador publicó tendencias nuevas en `newsletter` esta semana?
- [ ] ¿El Analista reportó ángulos sub-representados?

Si no hay nada pendiente → no ejecutar.

## 2. Decidir qué hacer

**Si hay guión para revisar** → ir al paso 3a (QA loop)
**Si hay decisión de contenido semanal** → ir al paso 3b (coordinación semanal)
**Si hay issue específico del CEO** → ejecutarlo

## 3a. QA loop (revisión de guión)

1. Leer el guión completo en Supabase:
   ```
   GET https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/guiones?status=eq.borrador&order=created_at.desc
   ```

2. Evaluar con el checklist de los 6:
   - ✅ ¿Construye referente? (no vendedor)
   - ✅ ¿Dato fresco? (no quemado — ver lista en escritor/soul.md)
   - ✅ ¿Hook con postura? (no neutro)
   - ✅ ¿Cierre fuerte? (opinión clara, no vaga)
   - ✅ ¿Voz Santiago? (rioplatense, datos conversacionales)
   - ✅ ¿Texto mínimo 200 palabras?

3. Si pasa todos los criterios → cambiar `status` a `listo`
4. Si falla alguno → crear issue para el Escritor con feedback concreto:
   - Qué criterio falla
   - Cómo mejorar específicamente (no "mejorá el tono", sino "el cierre es tibio, necesita tomar postura sobre X")

## 3b. Coordinación semanal

1. Revisar pipeline:
   ```
   GET /rest/v1/guiones?status=eq.listo&select=count
   ```
2. Si hay menos de 5 guiones listos → despertar al Escritor con contexto de tendencias actuales
3. Revisar si el Analista reportó ángulos sub-representados → incluir ese dato en el brief al Escritor

## 4. Reportar en Supabase

```
POST https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/reportes
Headers: apikey + Authorization: Bearer sb_publishable_HmiBL9VpEhaYyPqjA1v67w_F38x48El
Body: {
  "titulo": "CMO: [revisión guión / coordinación semanal] — dd/mm/aaaa",
  "agente": "CMO",
  "contenido": "Qué hice, qué guiones aprobé, qué devolví al Escritor y por qué"
}
```
