# Guiones SFRE

Dashboard con **124 guiones** para reels y TikTok de Santiago Funes Real Estate, más el framework, voz y datos para generar nuevos.

## Dónde vive qué

- **Dashboard con los 124 guiones:** [index.html](index.html) — single-file HTML con todos los guiones embebidos como array JS. Deployado en https://santiagomfunes-crypto.github.io/dashboard-guiones/ (remote `origin` = `santiagomfunes-crypto/dashboard-guiones`).
- **Feedback e ideas:** [feedback.json](feedback.json), [ideas.json](ideas.json) — capturados desde el dashboard (requiere token de GitHub en ⚙️ para sincronizar, ver memoria del proyecto).
- **Framework para generar nuevos:** [referencia/](referencia/) (voz, ángulos, datos Tandil), [contexto/](contexto/) (info negocio y personal).
- **Comando `/guion`:** [guion.md](guion.md) + [guion-command.md](guion-command.md). Al correrlo, genera un guion nuevo usando el framework y lo guarda en [salidas/](salidas/).

## Para agregar un guion nuevo al dashboard

El dashboard embebe los guiones como array en [index.html](index.html) (buscar `const guiones = [`). Agregar al final del array con el mismo formato (id, tema, t, ang, hook, text) y pushear al remote.

## Relacionado

- Cerebro del negocio: `~/Desktop/Claude/sfre-gestion/`
- Otras herramientas: `~/Desktop/Claude/{tasador,propiedades,sf-pdf-generator}/` (por ahora; empezando a organizar todo bajo `~/Desktop/herramientas/inmobiliaria/`)
