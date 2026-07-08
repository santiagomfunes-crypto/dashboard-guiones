# Arreglar el sistema, no la instancia

> Paso de auto-mejora del sistema Fable 5. Atado a [matriz-modelos.md](matriz-modelos.md)
> y al [verificador](../.claude/agents/verificador.md).
> Principio: un output malo es un **síntoma**. Si arreglás solo ese output, el próximo
> sale igual de mal. La mejora es propiedad del sistema, no del modelo.

## La regla

Cuando un guion se descarta, un scraper trae basura, una landing no convence, o Santi
corrige lo mismo dos veces: **antes de re-hacer la instancia, preguntate qué archivo del
sistema tendría que haber evitado esto.** Arreglás ese archivo. Después re-hacés la instancia
con el sistema ya corregido.

## Adónde va cada arreglo

| Falla observada | Qué archivo se corrige |
|---|---|
| Guion genérico / sin enfoque / se descarta | `referencia/framework-angulos.md` (falta un enfoque o un anti-patrón) o `voz-santiago.md` (dato quemado nuevo) |
| El verificador dejó pasar algo que Santi rechazó | `.claude/agents/verificador.md` (agregar el criterio o la red flag que faltó) |
| Se repite un tema/anécdota o falta una historia | `referencia/respuestas-santiago/` (agregar/actualizar el banco) |
| Se usó el modelo caro para algo mecánico (o al revés) | `referencia/matriz-modelos.md` (afinar la regla de ruteo) |
| Un scraper trae datos malos o rompe | el script del scraper + nota en la memoria de bloqueos de scraping |
| Santi corrigió un comportamiento de trabajo | una **memoria `feedback`** (con **Why** y **How to apply**) |

## El bucle correcto

1. **Diagnosticá la causa raíz**, no el síntoma. "Este guion es flojo" → ¿por qué el
   sistema lo dejó pasar? ¿Faltaba un criterio, un dato, un ejemplo, una red flag?
2. **Corregí el archivo del sistema** (tabla de arriba). Un cambio chico y concreto.
3. **Re-hacé la instancia** con el sistema ya corregido y verificá de nuevo.
4. Si la falla vino de una corrección de Santi, **guardala como memoria `feedback`** para
   que no se pierda al compactar.

## Anti-patrón

Re-escribir el output diez veces sin tocar el sistema. Si te ves haciendo el mismo fix
manual dos veces, el fix va en el archivo, no en el output. Eso es lo que hace que el
sistema mejore solo con el uso.
