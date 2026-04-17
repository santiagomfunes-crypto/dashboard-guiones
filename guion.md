# Guion para Reel

> Generá un guion de reel para TikTok/Instagram con tono orgánico, datos duros y la voz de Santiago Funes.

## Variables

tema: $ARGUMENTS (el tema del reel — ej. "crecimiento de Tandil", "por qué invertir", "responder a los que dicen que Tandil era mejor antes")

---

## Instrucciones

### Paso 1: Cargar contexto

Leé estos archivos en orden:

1. `guiones/referencia/voz-santiago.md` — tono y estilo
2. `guiones/referencia/framework-angulos.md` — ángulos disponibles
3. `guiones/referencia/datos-tandil.md` — datos para usar
4. `guiones/contexto/info-personal.md` — identidad de Santiago
5. `guiones/contexto/info-negocio.md` — servicios del negocio

### Paso 2: Elegir ángulo

Basándote en el tema pedido, sugerí el mejor ángulo del framework. Si el usuario especificó un ángulo, usá ese. Si no, elegí el más potente para el tema y explicá por qué.

Los ángulos disponibles son:
- **Problema**: mostrar un dolor real
- **Solución**: presentar la respuesta
- **Producto**: posicionar Tandil/la inversión como oportunidad
- **Contrario**: desafiar lo que la mayoría piensa
- **Autoridad**: hablar desde la experiencia personal
- **Predicción**: proyectar el futuro con datos
- **Comparación**: comparar con otra ciudad/mercado
- **Historia**: contar un caso real

### Paso 3: Generar el guion

Generá el guion siguiendo estas reglas:

**Formato:**
- Solo texto hablado, entre comillas, párrafo por párrafo
- Duración: 45-90 segundos hablados (aproximadamente 150-250 palabras)
- Sin indicaciones de cámara dentro del guion (eso va aparte)

**Estructura obligatoria:**
1. Hook (primera frase que engancha — dato, afirmación fuerte, o provocación)
2. Desarrollo (datos + contexto + opinión, fluidos, sin preguntas retóricas)
3. Cierre (opinión fuerte de Santiago, sin llamada a la acción de venta)

**Reglas de tono (referirse a voz-santiago.md):**
- Español rioplatense (vos, tenés, laburar, pibes, posta)
- Conversacional, como hablando con un amigo
- Los datos se dicen de memoria, no se presentan formalmente
- Pro-desarrollo siempre
- Sin preguntas retóricas tipo "¿Sabías que...?"
- Sin cierre de venta tipo "escribime"
- Sin muletillas forzadas

**Reglas de datos (referirse a datos-tandil.md):**
- Usar mínimo 3 datos duros del archivo de referencia
- No inventar datos
- Si se necesitan datos que no están en el archivo, buscar en web y verificar

### Paso 4: Formato de video

Después del guion, generá:

**Textos en pantalla** — 3-5 textos cortos que aparecen durante el reel reforzando los datos clave. Formato: dato en grande, estilo de la marca (navy, gold, Bebas Neue para números).

**Caption para Instagram** — Corto, con dato gancho, máximo 10 hashtags relevantes.

**Caption para TikTok** — Una línea + hashtags relevantes.

### Paso 5: Guardar

Guardá el guion generado en `guiones/salidas/` con el formato:
`YYYY-MM-DD-{tema-corto}.md`

---

## Ejemplo de uso

`/guion responder a los que dicen que Tandil era mejor antes`
`/guion por qué Tandil es la mejor inversión de Argentina`
`/guion el problema de alquilar en Tandil`
