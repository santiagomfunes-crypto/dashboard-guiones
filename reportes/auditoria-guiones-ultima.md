# Auditoría del backlog de guiones "listo" — destrabar stock

30 guiones en `status='listo'` nunca filmados. Objetivo: identificar qué grabar ya y qué frena el stock.

**Hallazgo transversal:** 17 de 30 guiones (57%) están por debajo del mínimo de 200 palabras que exige `voz-santiago.md` ("Menos de 200 = incompleto. No guardar"). Eso reduce a **13 guiones realmente listos para cámara**. El Top 8 sale exclusivamente de ese grupo.

## Filmá estos primero

| # | Guion | Ángulo/enfoque | Por qué performa |
|---|---|---|---|
| 1 | **WJUL10** — El placard sin fondo | Historia/Autoridad | Es el ejemplo canónico de la voz de Santi: error concreto, sin excusas, cierre con sistema. 225 palabras, cero riesgo de dato quemado, atemporal. |
| 2 | **CU1** — Tandil está creciendo donde nadie mira | Predicción | Tandil-creciendo puro: comparación de lotes por zona, expansión urbana (+77% vs 35% nacional). Ancla en autoridad ("900 propiedades"), no en el dato solo. |
| 3 | **CU2** — Por qué la gente de Buenos Aires elige Tandil | Autoridad | Crecimiento + toca seguridad sin evadirla ("no te voy a decir que Tandil no tiene inseguridad"). Cierre de opinión, no de venta. |
| 4 | **WJUL9** — Nunca hubo tantos deptos para alquilar en Tandil | Contrario | Dato fresco y local (CEMART, mayo 2026), lee el mercado en tiempo real. Espaciar de #8 (60e196e9), tocan el mismo dato. |
| 5 | **WJUL7** — Un cliente quería comprar en pozo. Le dije que se compre el usado | Autoridad | Historia real con conflicto y resultado, enseña sin vender, dato de costo de construcción anclado a la anécdota. |
| 6 | **WJUL5** — Terrenos por Instagram sin aprobación municipal | Problema | Único del Top 8 que toca directamente seguridad/estafa inmobiliaria. Timely, cita a CEMART, protege al espectador sin vender. |
| 7 | **AUT-22A** — Lo que nadie me enseñó siendo agente a los 22 | Autoridad | 335 palabras, historia personal sin red flags, construye marca sin vender nada. El guion más completo del backlog. |
| 8 | **60e196e9** — Hace dos años no había depto para alquilar, hoy sobran | Solución | Antes/después con fuente citada (CEMART), mensaje pro-construcción sin nombrar políticos. Filmar espaciado de #4 (mismo dato de sobreoferta). |

## A rehacer o descartar

| Guion | 🔴/🟡 | Fix clave o motivo |
|---|---|---|
| WJUL4 — Tandil 10° para vivir, 72° para comprar (263w) | 🔴 | Duplicado casi exacto de db6628ae: mismo dato (Índice Hábitat Urbano 7,79/3,89), mismo mensaje. Además "creció 20% en población en una década" pisa el dato quemado 20,5% vs 14,8%. Quedarse con uno, descartar el otro. |
| db6628ae — Top 10 para vivir, puesto 72 para comprar (256w) | 🔴 | Duplicado de WJUL4, cierre más débil. Descartar este y quedarse con WJUL4. |
| f2dd0937 [E3] Polémicos — matrícula (56w) | 🔴 | Viola la regla explícita "nunca corrección pública de colegas" ("todos mis colegas están indignados... yo pienso distinto") y además está muy por debajo del mínimo de 200 palabras. Reescribir sin señalar al gremio, o descartar. |
| WJUL8 — Crédito barato, 89% compra en efectivo (226w) | 🟡 | Dato crudo como protagonista: 5+ cifras nacionales encadenadas con poca conexión a Tandil. Además redundante en tema con WJUL6. Cortar a 2 datos, anclar a un caso local, espaciar de WJUL6. |
| WJUL6 — ¿Conviene sacar crédito ahora? (253w) | 🟡 | Tercer guion del backlog sobre crédito hipotecario (junto a WJUL8 y los fragmentos de crédito abajo). Bueno igual, pero no publicar en la misma tanda que los otros. |
| 69d68fa5 — Tandil puede duplicar su población sin expandirse (274w) | 🟡 | Nombra a un exfuncionario con cargo ("exsecretario de Obras Públicas") — roza la regla de no nombrar políticos. Fix: atribuir a "un urbanista consultado" sin cargo institucional. |
| dcc3b90b [E4] Marca Personal (54w) | 🟡 | Roza vender-de-más en video top-of-funnel: "convenzo gente de que apostar a Tandil es la mejor decisión de su vida". Además muy corto. Fix: quitar "convenzo/vendo", reformular como reflexión de propósito, y completar a 200+ palabras. |
| 20eae242 — La esquina de Tandil que no vas a reconocer (165w) | 🟡 | Voz y cierre perfectos, pero 35 palabras por debajo del mínimo. Fix: sumar un ejemplo concreto de zona/barrio para llegar a 200+. |
| 36f394d7 — Todos se fueron a Buenos Aires. Yo me quedé. (160w) | 🟡 | Mismo problema de longitud. Fix: sumar un ejemplo numérico (costo de vida, competencia) para completar el cuerpo. |
| 840f40f8 — El tránsito no es culpa del crecimiento (174w) | 🟡 | Corto y sin gancho explícito a Tandil-creciendo, queda como queja aislada. Fix: cerrar con el dato de crecimiento poblacional y completar longitud. |
| 01e57cc0 — El finde largo: Tandil deja de ser nuestra (161w) | 🟡 | Corto y con tono cercano a queja de residente sin ángulo inmobiliario. Fix: sumar gancho de negocio (alquiler temporario) y completar longitud. |
| 2d7a0e24 — El "trabajo seguro" es el consejo más peligroso (162w) | 🟡 | Corto y cero Tandil/inmobiliario. Fix: atarlo a una decisión inmobiliaria concreta y completar longitud. |
| 6ca2acc5 — En mi casa no se hablaba de plata (169w) | 🟡 | Mismo problema: corto y sin gancho de nicho. Mismo fix que el anterior. |
| 144b4753 [E5] Tandil — las grúas (47w) | 🟡 | Hook fuerte, pero fragmento de 47 palabras (24% del mínimo). Fix: expandir con credencial + cuerpo + cierre de opinión antes de filmar. |
| c8b91686 [E2] Tandil — "era mejor antes" (51w) | 🟡 | Hook calcado literalmente del ejemplo del framework de ángulos, se siente plantillero. Además muy corto. Fix: reescribir con anécdota propia y completar a 200+. |
| db0b5914 [E1] Mentalidad (58w) | 🟡 | Buena voz, cero Tandil/inmobiliario, y muy corto. Fix: completar cuerpo y atarlo al negocio. |
| 05cb2d23 [E6] Crédito — 7 años sin crédito (55w) | 🟡 | Corto + cuarto guion del backlog sobre crédito hipotecario. Fix: completar longitud y espaciar de WJUL8/WJUL6 si se filma. |
| 1a3dc8a0 [E5] Crédito — la cola del banco (62w) | 🟡 | Corto + quinto guion sobre crédito. Fix: completar longitud, evitar saturar el tema en una misma tanda. |
| 68924afc [E5] Escena — el local vacío (47w) | 🟡 | Buen hook, muy corto. Fix: completar con cuerpo y cierre de opinión. |
| bf9e1f9e [E7] Inversión — ¿conviene comprar ahora? (57w) | 🟡 | Cierre ("la pregunta es con qué herramientas") suena a gancho de asesoría, no a opinión cerrada — riesgo de vender de más. Además muy corto. Fix: cerrar con opinión pura y completar longitud. |
| 378ea1df [E1] Crédito — mi primer crédito (63w) | 🟡 | Corto + sexto guion sobre crédito. Fix: completar longitud, espaciar del resto de la serie de crédito. |
| 1edde04b [E2] Mentalidad — "nunca vas a tener toda la plata" (54w) | 🟡 | Corto + séptimo guion que toca crédito/ahorro. Fix: completar longitud; el tema crédito ya está sobrerrepresentado en el backlog. |

## Los 3 patrones de falla más repetidos

1. **Fragmentos de hook marcados "listo" sin completar el guion.** 11 de 30 (37%) tienen 47-63 palabras — un cuarto del mínimo de 200 que exige la guía de voz. Son ideas fuertes que nunca se llevaron a cuerpo completo y no debieron salir del QA loop en ese estado.
2. **Zona gris de longitud.** Otros 6 guiones (20eae242, 36f394d7, 840f40f8, 01e57cc0, 2d7a0e24, 6ca2acc5) tienen voz y estructura completas pero están 26-40 palabras por debajo del mínimo — a un ajuste menor de ser filmables.
3. **Backlog sin control de duplicados ni de saturación temática.** WJUL4 y db6628ae son el mismo guion con dos IDs distintos, y 6 guiones separados (WJUL8, WJUL6, 05cb2d23, 1a3dc8a0, 378ea1df, 1edde04b) tocan crédito hipotecario — si se filman todos juntos, el contenido compite consigo mismo en el feed.
