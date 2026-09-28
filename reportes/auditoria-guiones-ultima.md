# Auditoría del backlog de guiones "listo" — destrabar stock

30 guiones en `status='listo'` sin filmar. **Mismo backlog exacto que la auditoría del 2026-09-14 — cero movimiento en dos semanas.** Objetivo: elegir qué grabar ya, no generar más.

## Filmá estos primero

| # | Guion | Ángulo/enfoque | Por qué performa |
|---|---|---|---|
| 1 | **CU2** — Por qué la gente de Buenos Aires elige Tandil para vivir | Autoridad/Comparación | Combina los dos ejes prioritarios: crecimiento (Parque Industrial 72 empresas, Cluster Tecnológico, UNICEN) + seguridad tratada con honestidad ("no te voy a decir que Tandil no tiene inseguridad"). Precios BA vs Tandil verificados contra datos-tandil.md. Cierre firme, cero CTA. |
| 2 | **WJUL10** — El día que llevé a un cliente a ver un placard sin fondo | Historia/Testimonio | Es la anécdota que voz-santiago.md cita como modelo de "lo que sí funciona". Error propio sin excusas, cierre en sistema/proceso, cero riesgo de dato vencido. |
| 3 | **69d68fa5** — Tandil puede duplicar su población sin expandirse | Contrario | Único guion que ataca de frente el eje "desarrollo urbano" (densificación vs. expansión), citando a un urbanista real. Responde a la queja típica del cemento con opinión incómoda y no obvia. |
| 4 | **CU1** — Tandil está creciendo donde nadie mira | Predicción | Cada dato cruza limpio contra la referencia vigente: Tesla XXI (135 entregadas + 52 en obra), planta municipal de hormigón ($395M), expansión urbana 77,2% vs 35% nacional. Credencial real (900+ propiedades en base). |
| 5 | **WJUL9** — Nunca hubo tantos deptos para alquilar en Tandil. Y los dueños no bajan un peso | Contrario/Problema | La cita de la presidenta del CEMART (mayo 2026, "nunca hubo tanta oferta") está tomada literal de la fuente vigente. Dato de mercado actual, no quemado, cierre con opinión propia. |
| 6 | **840f40f8** — El tránsito no es culpa del crecimiento, es del municipio | Problema | Postura pro-desarrollo que distingue crecimiento (bueno) de mala gestión (municipio), sin nombrar políticos. Encaja con "pro-desarrollo, firme" de la voz. |
| 7 | **WJUL5** — Terrenos por Instagram sin aprobación municipal | Problema | Único guion que toca de frente la estafa inmobiliaria ligada al boom de loteos. Protege al espectador en vez de venderle; cierra con consejo práctico y verificable. |
| 8 | **20eae242** — La esquina de Tandil que no vas a reconocer | Contrario | Observación personal ("entro a un montón de casas por mes") + crecimiento urbano concreto. Reconoce lo que se perdió sin caer en nostalgia ni en tono turístico. |

*Reserva evergreen sin riesgo de dato (no entraron por espacio, no por defecto): `WJUL7` (pozo vs. usado, dato de costo de construcción +118% USD correctamente citado) y `dd3ce152` (el cliente que perdí por callarme). Intercalar entre los de arriba.*

---

## A rehacer o descartar

| Guion | 🔴/🟡 | Fix clave o motivo |
|---|---|---|
| WJUL8 — Crédito barato, 89% compra sin usarlo | 🔴 | Dato falso contra la referencia vigente: cita "ICBC 6,9% + UVA" cuando datos-tandil.md marca ICBC al **10,5%** (bajando desde 11%) — la tasa más baja real es Banco Nación al 6%. También afirma "el crédito cayó 54% en mayo, cinco meses seguidos", cifra no verificable contra la fuente. Reescribir con tasas de marzo 2026 antes de filmar. |
| c8b91686 — [E2] Tandil ("era mejor antes") | 🔴 | Incompleto (~52 palabras) **y** el hook es copia casi literal del ejemplo de `framework-angulos.md` para el ángulo Contrario. Nunca se escribió una versión propia. Descartar y reescribir desde cero. |
| f2dd0937 — [E3] Polémicos (matrícula) | 🔴 | Incompleto (~56 palabras). Además viola una regla explícita de voz-santiago.md ("NUNCA: corrección pública de colegas"): "Todos mis colegas están indignados... yo pienso distinto". Reformular sin señalar al gremio y expandir. |
| dcc3b90b — [E4] Marca Personal | 🔴 | Incompleto (~54 palabras). El hook ("convenzo gente de que apostar a Tandil es la mejor decisión de su vida") roza vender-de-más en video top-of-funnel. |
| bf9e1f9e — [E7] Inversión | 🔴 | Incompleto (~57 palabras) + cierre con presión de urgencia ("hoy paga un 20% más") cercano al CTA de venta. Expandir y suavizar cierre. |
| 05cb2d23 — [E6] Crédito | 🔴 | Incompleto (~60 palabras). Cierre "no lo dejes pasar de nuevo" roza urgencia de venta. Fusionar con WJUL6/WJUL8 en un solo guion completo. |
| 1edde04b — [E2] Mentalidad | 🔴 | Incompleto (~54 palabras). Cierre binario ("el que arranca vs. el que mira desde afuera") linda con motivación vacía, prohibida en la guía de voz. |
| 378ea1df — [E1] Crédito | 🔴 | Incompleto (~63 palabras). Suma al eje crédito ya sobrecargado (5 guiones distintos tocan crédito hipotecario). Consolidar, no expandir uno más. |
| 1a3dc8a0 — [E5] Crédito (cola del banco) | 🔴 | Incompleto (~62 palabras), mismo eje crédito sobrecargado. |
| 144b4753 — [E5] Tandil (grúas) | 🔴 | Incompleto (~47 palabras), pero el mejor hook del lote de outlines ("conté nueve grúas... votan con obra"). Priorizar su expansión por sobre los demás `[E#]`. |
| 68924afc — [E5] Escena (local vacío) | 🔴 | Incompleto (~47 palabras), outline sin desarrollar. Buen ángulo solución, pero no es un guion filmable. |
| WJUL4 — Tandil 10° para vivir, 72° para comprar | 🔴 | Duplica a `db6628ae` (mismo hallazgo, mismo título). Además parafrasea un dato quemado ("creció 20% en la década" ≈ 20,5% vs 14,8% nacional). Descartar. |
| db6628ae — Tandil: top 10 para vivir, puesto 72 para comprar | 🟡 | Sin dato quemado, mejor ejecutado que WJUL4, pero el "Índice de Hábitat Urbano / puesto 72" no tiene fuente citable en datos-tandil.md. Verificar la fuente real antes de filmar. |
| WJUL6 — ¿Conviene sacar crédito ahora? | 🟡 | Completo y con buena voz, pero nunca menciona Tandil y comparte el insight "9 de cada 10 sin crédito" con WJUL8. Anclar a un caso local o descartar uno de los dos. |
| 60e196e9 — Hace dos años no había un depto, hoy sobran | 🟡 | Buen cierre ("el ladrillo resuelve más que un decreto"), pero repite la misma cita CEMART/mayo 2026 que WJUL9 (ya en el top 8) desde el ángulo solución. Espaciar varias semanas si se filma. |
| WJUL7 — Un cliente quería comprar en pozo | 🟡 | Sin defecto — dato de costo de construcción (+118% USD) verificado. Prioridad 2 solo por no tocar el eje Tandil-crecimiento explícitamente. |
| dd3ce152 — El primer cliente grande que perdí por callarme | 🟡 | Sin defecto, voz e integridad al 100%, evergreen. Prioridad 2 por no tocar el eje crecimiento/desarrollo. |
| AUT-22A — Lo que nadie me enseñó a los 22 | 🟡 | Voz sólida y completo, pero mezcla tres lecciones en un guion y no toca Tandil ni mercado. Cortar a una sola lección. |
| 01e57cc0 — El finde largo: Tandil deja de ser nuestra | 🟡 | Voz correcta, pero autoridad floja: es observación de vecino, no de agente inmobiliario, y no conecta con el negocio. |
| 2d7a0e24 — El "trabajo seguro" es el consejo más peligroso | 🟡 | Voz perfecta, pero cero Tandil / cero inmobiliario. Dejar como contenido secundario de marca personal. |
| 6ca2acc5 — En mi casa no se hablaba de plata | 🟡 | Mismo caso: fuerte en voz, genérico, sin anclaje a Tandil ni al negocio. |
| 36f394d7 — Todos se fueron a Buenos Aires. Yo me quedé | 🟡 | Buen ángulo interior-vs-capital, completo. Sumar un dato concreto de Tandil (ej. 1.000 porteños/año) para subir de prioridad. |

---

## Patrones de falla más repetidos

1. **Outline guardado como "listo"**: 10 de 30 guiones (todos los `[E1]-[E7]` más la Escena) tienen 47-63 palabras, muy por debajo del piso de 200 que fija voz-santiago.md — son ideas de hook sin cuerpo. La mitad de esos stubs además viola reglas explícitas de la guía (corrección pública de colegas en `f2dd0937`, urgencia de venta en `bf9e1f9e`/`05cb2d23`, vender-de-más en `dcc3b90b`) — no solo faltan, están mal encaminados.
2. **Duplicados y saturación temática sin control**: `WJUL4` y `db6628ae` cubren el mismo hallazgo con dos IDs distintos; `WJUL9` y `60e196e9` repiten la misma cita CEMART desde ángulos problema/solución; el eje "crédito hipotecario" por sí solo ocupa 5 guiones (`WJUL8`, `WJUL6`, y tres `[E#]`) que se canibalizan entre sí.
3. **Datos sin control de vigencia contra la referencia**: `WJUL8` cita una tasa de ICBC (6,9%) que hoy es directamente falsa contra datos-tandil.md (10,5%); `WJUL4`/`db6628ae` usan un índice ("Hábitat Urbano") sin fuente citable en la referencia. Nadie está cruzando estos números antes de marcar un guion como "listo".
