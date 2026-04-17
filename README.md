# Guiones — Reels / TikTok para Santiago Funes

Generador de guiones con voz y framework ya calibrados. Copiado desde `marketing-guiones/` el 2026-04-14 (original intacto).

## Cómo usar

Desde Claude Code, en este workspace:

```
/guion [tema del reel]
```

Ejemplos:
- `/guion por qué Tandil es la mejor inversión de Argentina`
- `/guion el problema de alquilar en Tandil`
- `/guion responder a los que dicen que Tandil era mejor antes`

El comando carga automáticamente voz, framework de ángulos PPOS, datos frescos de Tandil, y genera guion + textos en pantalla + captions. Lo guarda en `guiones/salidas/`.

## Estructura

```
guiones/
  referencia/
    voz-santiago.md        ← tono y estilo del guion
    framework-angulos.md   ← 8 ángulos disponibles (PPOS extendido)
    datos-tandil.md        ← datos duros para citar
  contexto/
    info-personal.md       ← identidad de Santiago
    info-negocio.md        ← servicios del negocio
    datos-actuales.md      ← datos que se actualizan
  salidas/                 ← guiones generados con fecha
  guion-command.md         ← copia del comando (referencia)
```

El slash command vive en `.claude/commands/guion.md`.
