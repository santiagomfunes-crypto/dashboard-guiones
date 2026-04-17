# Heartbeat — Agente Publisher

## 1. Wake-up check

- [ ] ¿Hay guiones con status "filmado" que tengan variantes generadas pero sin briefing?
- [ ] ¿Hay variantes con metricas cargadas (tasa_finalizacion > 0) sin ganador marcado?
- [ ] ¿Que hora es? Mañana = briefing de publicacion. Tarde = reporte de ganador.

## 2. Decidir que hacer

**Si hay guiones filmados con variantes sin briefing** → generar briefing de publicacion.

**Si hay variantes con metricas sin ganador** → generar reporte de ganador con captions para 4 plataformas.

**Si no hay nada pendiente** → no ejecutar. Reportar "sin contenido pendiente de publicar".

## 3. Ejecutar

### 3a. Briefing de publicacion
1. Leer guiones con status "filmado" de Supabase
2. Leer variantes de cada guion
3. Para cada variante: escribir caption optimizada para TikTok (prueba)
4. Agregar hashtags relevantes al tema
5. Incluir horario sugerido
6. Dejar briefing como comentario en el issue

### 3b. Reporte de ganador
1. Leer variantes con tasa_finalizacion > 0
2. Identificar la de mayor tasa por guion
3. Marcar como tipo="ganador" en Supabase
4. Escribir captions adaptadas para: Instagram, TikTok, YouTube Shorts, Facebook
5. Incluir hashtags optimizados por plataforma
6. Dejar reporte como comentario en el issue

## 4. Verificar calidad

- [ ] ¿Las captions suenan a Santiago, no a community manager generico?
- [ ] ¿Los hashtags son relevantes al tema especifico, no genericos?
- [ ] ¿El briefing es copy-paste ready para Celina?
- [ ] ¿Identifique correctamente al ganador por tasa de finalizacion?

## 5. Reportar

- Cuantos briefings genero
- Cuantos ganadores identifico
- Si algun guion filmado no tiene variantes (avisar para que se generen)
