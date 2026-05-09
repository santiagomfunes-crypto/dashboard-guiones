# Brand Context — Santiago Funes RE
> Archivo compartido por todos los agentes. Leer al iniciar cualquier tarea que toque contenido, voz o estrategia.
> Fuente de verdad: voz-santiago.md, estrategia-marca.md, framework-angulos.md.

---

## Quién es Santiago

- 22 años, Tandil, Buenos Aires. Martillero y corredor inmobiliario.
- Vivió en Costa Rica y Europa. No es un pibe sin mundo.
- Usa IA y sistemas propios: 900+ propiedades en base de datos. Su ventaja es infraestructura.
- Trabaja con pocas inmobiliarias de confianza (calidad sobre cantidad).
- Primera venta: un cliente de la madre. No fue épico. Lo dice así.
- Lo denunciaron por hacer ruido en redes. El gremio en contra, los clientes a favor.

## Posicionamiento

**Referente inmobiliario**, no vendedor. El contenido construye autoridad — los boletos son consecuencia.
- Referentes del método: Beltrán Briones (puerta de atrás), Fran Castro (omnipresencia + test reels)
- Ángulos válidos: real estate Tandil, finanzas personales argentinas, mentalidad, economía argentina, Tandil lifestyle, historia personal
- Ángulos prohibidos: motivación vacía, tips genéricos, corrección pública de colegas

## Voz

- **Rioplatense natural**: "vos", "pibes", "laburo", "posta", "verso"
- **Dato como si lo supiera de memoria** — nunca "según estadísticas..."
- **Opinión fuerte al cierre** — nunca tibio, nunca "depende"
- **Orgánico, no guionado** — suena a charla, no a informe
- **Complejiza en lugar de simplificar** — no rechaza frases, las discute

## Los 6 NOs (validados por Santiago)

1. No pibe rico — no ostentar ni simular
2. No motivación vacía — "vos podés" / "los sueños se cumplen"
3. No corrección pública de colegas o clientes
4. No tips genéricos que cualquier cuenta publica
5. No pedir engagement explícitamente
6. No traje en cámara — vestimenta casual y auténtica

## Contexto estratégico actual (mayo 2026)

- **5 Trial Reels/día en Instagram** — los ganadores van a 4 plataformas
- **Sesiones batch**: filman ~10 guiones por sesión, el sistema distribuye en 2 semanas
- **Sofía** (WhatsApp bot de Altavista Otero): 100% funcional, capta leads desde el sitio web
- **Altavista Otero**: proyecto de inteligencia inmobiliaria B2B, datos de cierre reales
- **sfre-web**: propiedades.santiagofunes.com.ar — Next.js/Vercel/Supabase

## Prioridades del sistema de contenido

1. Guiones con hook fuerte + postura clara + dato fresco
2. Formato Briones: torneo / lo-que-nadie-te-dice / números-que-no-cierran / opinión-impopular
3. Framework PPOS+ (de Ramiro Curía): ver `referencia/framework-angulos.md`
4. Duración objetivo: 45-90 segundos leído en voz alta

## Supabase — tablas principales

| Tabla | Para qué |
|---|---|
| `guiones` | guiones escritos por el Escritor |
| `newsletter` | entradas del Investigador como input |
| `ideas` | ideas sin desarrollar |
| `agent_memories` | aprendizajes persistentes cross-agente (importance 1-10) |
| `reportes` | outputs de cualquier agente |
| `propiedades_mercado` | datos scrapeados por Arquitecto |

## IDs de agentes

```
CEO:          c0543ed4-2f1b-4f48-9014-422b6ebe911e
CMO:          272499de-2fd3-4e00-bb38-89c76b664bf7
Escritor:     cc38b20a-207a-43ff-8afd-d226cd721771
Investigador: 33ccac15-166f-4a93-8ec1-3cc939911c18
Analista:     0128b9ab-1387-4a8c-99fb-3d5edf267f09
Brain:        1d118a87-3637-40c5-a967-e25bbbbda204
SEO Writer:   c40d6d8b-483f-46bf-8feb-13cd8ae5e778
Price Tracker:6e36fdd1-f221-42f4-b645-434db2169e2e
Macro Analyst:10936ff6-8f2e-4d68-86b1-a186bd2df166
ROI Calc:     5a79f9aa-7607-4afb-840a-66bcd0987fd3
UX Designer:  e38f08d1-dd44-42ea-8893-ac0aa7a1c2e4
Arquitecto:   811a223b-b1fe-4693-9851-89c4d04ee23b
Auditor:      1cac5dbe-a3d2-4fd8-a45c-2e761a30aad6
```
