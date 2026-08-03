# Auditoría del backlog de guiones "listo" — destrabar stock

30 guiones en `status='listo'` nunca filmados. Objetivo: identificar qué grabar ya y qué frena el stock.

## Filmá estos primero

| # | Guion | Ángulo/enfoque | Por qué performa |
|---|---|---|---|
| 1 | **CU2** — Por qué la gente de Buenos Aires elige Tandil | Comparación/Autoridad | Precio Tandil vs Palermo + Parque Industrial/Globant + toca seguridad sin evadirla. Único guion que combina crecimiento y seguridad en un solo video, con cierre de opinión fuerte. |
| 2 | **CU1** — Tandil está creciendo donde nadie mira | Predicción | Expansión urbana (+77% vs 35% nacional) + zonas con lotes 6x más baratos. Hook geográfico accionable, cierre con urgencia implícita, no vende de más. |
| 3 | **69d68fa5** — Tandil puede duplicar su población sin expandirse | Contrario/Predicción | Ángulo polémico (densificación) respaldado por fuente con nombre y cargo real (ex-Secretario de Obras Públicas). Desarrollo puro, contesta la queja de "nos llenan de cemento". |
| 4 | **WJUL4** — Tandil: 10° para vivir, 72° para comprar | Contrario | Dato de índice verificable (Hábitat Urbano 7,79 vs 3,89) + cierre quotable ("las ciudades que mejoran no se abaratan, se encarecen"). Mejor versión del par duplicado con db6628ae — ver tabla. |
| 5 | **60e196e9** — Hace dos años no había depto para alquilar, hoy sobran | Solución | Antes/después con fuente citada (CEMART) + mensaje pro-construcción sin nombrar políticos. Resuelve tensión, no vende. |
| 6 | **WJUL5** — Terrenos por Instagram sin aprobación municipal | Problema | Alerta al comprador con autoridad clara + checklist accionable (plano, informe de dominio). Construye confianza, encaja con el boom de demanda de terrenos que trae el crecimiento. |
| 7 | **WJUL10** — El placard sin fondo | Historia | Estructura probada (error concreto → aprendizaje → sistema). Cero fricción, listo para grabar tal cual. |
| 8 | **WJUL8** — Crédito más barato en años, 89% compra en efectivo | Contrario | Dato duro y fresco (ICBC 6,9%+UVA, caída 54% crédito PBA) + interpretación propia (el ahorrista en dólares es el motor real). Autoridad basada en datos, no en opinión vacía. |

## A rehacer o descartar

| Guion | 🔴/🟡 | Fix clave o motivo de descarte |
|---|---|---|
| db6628ae — "Top 10 para vivir, puesto 72 para comprar" | 🔴 | Duplicado casi textual de WJUL4: mismo dato (Índice de Hábitat Urbano 7,79/3,89), mismo mensaje, cierre más débil. Descartar y quedarse con WJUL4. |
| WJUL9 — "Nunca hubo tantos deptos, los dueños no bajan" | 🟡 | Usa la misma fuente/dato que 60e196e9 (sobreoferta CEMART/Claudia Lutz). Espaciarlo varias semanas del #5 o fusionar en un solo guion — filmados juntos, el feed repite la misma estadística. |
| WJUL2 — "Inversores de Buenos Aires... el flujo se frenó" | 🟡 | Tiene preguntas retóricas ("¿Por qué llegaban? Fácil. ¿Por qué se frenó? También fácil."), prohibidas explícitamente en voz-santiago.md. Reescribir como afirmación directa antes de grabar. |
| dcc3b90b — [E4] Marca Personal ("convenzo gente de que Tandil es la mejor decisión de su vida") | 🔴 | Además de ser un fragmento de 76 palabras, la frase roza "vender de más" (afirmación absoluta tipo motivación vacía). Si se reescribe, bajar el tono de la promesa. |
| 10 guiones formato **[E1]–[E7]** restantes (144b4753, c8b91686, db0b5914, 05cb2d23, 1a3dc8a0, f2dd0937, 68924afc, bf9e1f9e, 378ea1df, 1edde04b) | 🟡 | Todos entre 60 y 80 palabras. La propia guía dice "menos de 200 palabras = incompleto, no guardar" — son ideas de hook válidas pero nunca se completaron a guion de 200-350 palabras. No filmar como están; expandir con credencial + cuerpo + cierre de opinión, o descartar. |

## Los 3 patrones de falla más repetidos

1. **Micro-guiones marcados "listo" sin cumplir el mínimo de 200 palabras.** 11 de 30 (37% del backlog) son fragmentos de hook de 60-80 palabras que nunca se completaron. La guía es explícita: eso no debería haber pasado a `listo` — nunca deberían haber salido del QA loop en ese estado.
2. **Mismo dato reciclado sin variación real entre guiones.** El Índice de Hábitat Urbano (WJUL4/db6628ae), la sobreoferta CEMART (WJUL9/60e196e9) y las "900 propiedades analizadas por IA" (CU1, WJUL3, WJUL10) aparecen repetidos. Sin espaciarlos, el contenido compite consigo mismo en el feed.
3. **Preguntas retóricas que la guía prohíbe explícitamente** (tipo "¿Y por qué se quedan?") se cuelan en al menos dos guiones (WJUL2, c8b91686), rompiendo la voz orgánica que se pide.
