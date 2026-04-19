# Guiones SFRE

Sistema de contenido para Santiago Funes Real Estate. Dashboard + agentes IA + base de datos en la nube.

## Arquitectura

- **Dashboard**: [index.html](index.html) — single-file HTML deployado en GitHub Pages (`santiagomfunes-crypto.github.io/dashboard-guiones/`)
- **Base de datos**: Supabase (tablas: guiones, variantes, newsletter, ideas, publicaciones, sesiones)
- **Agentes IA**: Paperclip con 10 agentes (soul files en `paperclip-agents/`)
- **Conocimiento**: `referencia/` (playbook, voz, datos, framework) + `youtube_brain/` (fuentes aprendidas)

## Credenciales

Viven en `.env` (gitignored) y en backup fuera del repo (`../backups/.env-guiones`). Supabase URL: `https://pgnmpxqljxrpnvexcygh.supabase.co`

## Usuarios del dashboard

- Santiago: santiagomfunes@gmail.com
- Celina: celina.colombo15@gmail.com
- Marcos: huergomarcos@gmail.com
- Password: santiago (todos)

## Estructura de carpetas

```
guiones/
├── index.html              ← dashboard (GitHub Pages)
├── supabase.min.js         ← SDK de Supabase (local, no CDN)
├── .gitignore
├── CLAUDE.md               ← este archivo
├── PARA-MARCOS.md          ← resumen para Marcos
├── contexto/               ← info del negocio y personal
├── referencia/             ← playbook, voz, datos, framework
├── paperclip-agents/       ← soul + heartbeat de cada agente
└── youtube_brain/          ← sistema de aprendizaje de fuentes
```

## Agentes Paperclip (10 activos)

| Agente | Qué hace | Frecuencia |
|---|---|---|
| Investigador | Busca tendencias del mercado | Cada 48h |
| Escritor | Escribe guiones + variantes de hook | Cada 72h |
| Publisher | Prepara briefings de publicación | Diario |
| Brain | Aprende de videos/web | On-demand |
| Analista | Analiza mix de contenido | Semanal |
| Price Tracker | Rastrea precios m² Tandil/CABA | Semanal |
| ROI Calculator | Calcula retorno de propiedades | On-demand |
| Macro Analyst | Resumen macro semanal | Semanal |
| SEO Writer | Convierte guiones en artículos | Semanal |
| UX Designer | Mejora el dashboard | On-demand |

## Backups

SQL y credenciales en `~/Desktop/herramientas/inmobiliaria/backups/` (fuera del repo).

## Para agregar un guion nuevo

Los guiones viven en Supabase, no en el HTML. Se agregan desde el dashboard o los genera el Escritor automáticamente.
