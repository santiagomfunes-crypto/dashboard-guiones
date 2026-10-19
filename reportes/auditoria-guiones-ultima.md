# Auditoría del backlog de guiones "listo" — destrabar stock

30 guiones en `status='listo'` sin filmar, mismos 30 de auditorías previas (05/10 y una tanda intermedia). Verificación independiente contra `voz-santiago.md`, `framework-angulos.md` y `datos-tandil.md`, con conteo de palabras y chequeo de cifras guion por guion.

## Filmá estos primero

| # | Guion | Ángulo/enfoque | Por qué performa |
|---|---|---|---|
| 1 | **CU2** — Por qué la gente de Buenos Aires elige Tandil para vivir | Autoridad/Comparación | Precio verificado (Palermo ~170k vs Tandil 60-80k), Parque Industrial (72 empresas) y Cluster Tecnológico cruzan correcto con la referencia. Seguridad tratada con honestidad, sin negarla. 268 palabras, cierre firme, cero CTA. |
| 2 | **CU1** — Tandil está creciendo donde nadie mira | Predicción | Expansión urbana 77,2% vs 35% nacional, Tesla XXI (135 entregadas + 52 en obra), lotes desde USD 17.000 — todo verifica exacto contra `datos-tandil.md`. Credencial real (900+ propiedades). |
| 3 | **WJUL10** — El día que llevé a un cliente a ver un placard sin fondo | Historia/Testimonio | La anécdota que `voz-santiago.md` cita textual como modelo de marca. 225 palabras, sin un solo dato que verificar, cierre en sistema/proceso. |
| 4 | **dd3ce152** — El primer cliente grande que perdí por callarme | Historia/Testimonio | Integridad y reputación, honestidad incómoda. Evergreen, sin fecha de vencimiento, sin cifras que puedan quedar desactualizadas. |
| 5 | **WJUL9** — Nunca hubo tantos deptos para alquilar en Tandil. Y los dueños no bajan un peso | Contrario | Cita a Claudia Lutz (presidenta CEMART, mayo 2026) atribuida y transcripta correcto. Ángulo crítico poco común, cierra con opinión propia. |
| 6 | **WJUL6** — ¿Conviene sacar crédito ahora? | Autoridad | "9 de cada 10 operaciones sin crédito" es consistente con la proporción real (ratio hipotecas/escrituras ~15-20% en 2025-2026). Completo, sin CTA. |
| 7 | **WJUL7** — Un cliente quería comprar en pozo. Le dije que se compre el usado | Autoridad | "El costo se duplicó en dólares" es coherente con el dato real (+118% desde oct 2023). Historia con final verificable, insight que no se escucha en el sector. |
| 8 | **60e196e9** — Hace dos años no había un depto, hoy sobran | Solución | Misma fuente CEMART que WJUL9 pero ángulo opuesto (pro-mercado, no pro-regulación): "el ladrillo resuelve más que cualquier decreto". **Espaciar varias semanas de WJUL9** por compartir la cita de origen. |

*Backup limpio, sin errores, fuera por redundancia temática: `AUT-22A` (335 palabras, voz sólida) es la 3ª historia de "arrancar en el rubro / error temprano" del backlog —junto a WJUL10 y dd3ce152, ya priorizados—. Rotarlo para la próxima tanda.*

---

## A rehacer o descartar

| Guion | 🔴/🟡 | Fix clave o motivo |
|---|---|---|
| **WJUL8** — Crédito barato, 89% compra sin usarlo | 🔴 | Cita ICBC a 6,9% + UVA; `datos-tandil.md` registra **10,5%** (bajando desde 11%). Además afirma que el crédito "cayó 54%... cinco meses seguidos" sin respaldo en la referencia (los datos muestran crecimiento fuerte de hipotecas en 2025). Dato falso en cámara — usar WJUL6 en su lugar. |
| **WJUL5** — Terrenos por Instagram sin aprobación municipal | 🔴 | Dice "el presidente del Centro de Martilleros"; la referencia identifica a **Claudia Lutz, presidenta CEMART** (confirmado también en WJUL9/60e196e9, que sí usan "presidenta" bien). Error de género sobre una persona real identificable — corregir antes de grabar. |
| **WJUL4** — Tandil 10° para vivir, 72° para comprar | 🔴 | El "Índice de Hábitat Urbano" (7,79/10, puesto 72) **no existe en `datos-tandil.md`** — no hay forma de verificarlo con la referencia actual. Duplica además a `db6628ae`. |
| **db6628ae** — Tandil: top 10 para vivir, puesto 72 para comprar | 🔴 | Mismo problema que WJUL4: cifra central sin fuente verificable. No usar ninguno de los dos hasta confirmar el origen del índice. |
| **69d68fa5** — Tandil puede duplicar su población sin expandirse | 🟡 | Pone "300.000 habitantes sin expandirse" en boca de un urbanista real (Guadagna) que no aparece en `datos-tandil.md`. Confirmar la declaración original antes de citar a una persona real en cámara. |
| **01e57cc0 / 2d7a0e24 / 20eae242 / 840f40f8 / 6ca2acc5 / 36f394d7** | 🟡 | Las seis están entre 160-174 palabras — bajo el piso de 200 que fija `voz-santiago.md` ("Menos de 200 = incompleto. No guardar"). Voz correcta en todas; `2d7a0e24` y `6ca2acc5` además no tienen ningún anclaje a Tandil/inmobiliario (son mindset/carrera genérico) — al expandirlas, atarlas al negocio. |
| **05cb2d23 / dcc3b90b / 1edde04b / bf9e1f9e / 144b4753 / f2dd0937 / 378ea1df / 1a3dc8a0 / c8b91686 / 68924afc** — bloque `[E1]-[E7]` + Escena | 🔴 | Los 10 son bocetos de 47-63 palabras, lejos del piso de 200 — nunca pasaron por credencial + cuerpo + cierre. `c8b91686` copia casi literal el hook de ejemplo de `framework-angulos.md` ("Tandil era mejor antes") en vez de ser contenido original. `f2dd0937` roza la corrección pública de colegas (regla prohibida). El eje crédito (`378ea1df`, `1a3dc8a0`, `05cb2d23`) está repetido en tres bocetos distintos — consolidar en uno solo al expandir. |

---

## Patrones de falla más repetidos

1. **Piso de 200 palabras incumplido en más de la mitad del backlog**: 16 de 30 guiones (10 bocetos `[E#]` de 47-63 palabras + 6 guiones "completos" de 160-174 palabras) nunca llegaron a la estructura hook+credencial+cuerpo+cierre que exige `voz-santiago.md`.
2. **Cifras y citas nunca cruzadas contra `datos-tandil.md` antes de marcar "listo"**: ICBC inventado en WJUL8, índice sin fuente en WJUL4/db6628ae, atribución de género incorrecta a la presidenta de CEMART en WJUL5, cita sin verificar puesta en boca de un urbanista real en 69d68fa5.
3. **El mismo hecho reciclado en guiones casi idénticos en vez de uno solo bien hecho**: ranking 10°/72° (WJUL4/db6628ae), sobreoferta de alquileres vía CEMART (WJUL9/60e196e9), y la historia de "arrancar en el rubro" repetida tres veces (WJUL10/dd3ce152/AUT-22A).
