# Meta Ads — Campaña Mayo 2026
**Grupo Alta Vista Otero · Tandil**
**Budget: USD 1.000/mes — 2 campañas**
*Actualizado 02/05/2026 — post reunión Leonel Paez*

---

## RESUMEN EJECUTIVO

| Campaña | Grupo | Budget | Ad Sets |
|---|---|---|---|
| C1 | Deptos e Inversión | **$600** | 5 sets testing → 2 ganadores |
| C2 | Casas y Premium + Retargeting | **$400** | 2 sets adquisición + 1 retargeting |

---

## ANTES DE LANZAR — AUDIENCIAS

### 1. Custom Audience (base propia)
- Exportar todos los contactos: mails + teléfonos del CRM/WhatsApp
- Meta → Audiences → Create → Custom Audience → Customer list → subir CSV

### 2. Lookalike 1% Argentina ← usar en C1 y C2
- Desde la Custom Audience recién creada
- Meta → Audiences → Create → Lookalike → Source: base propia → País: Argentina → 1%

### 3. Retargeting 180 días ← usar en C2
- Meta → Audiences → Create → Custom Audience → Meta sources
- Incluir: Instagram, Facebook, Lead forms — últimos 180 días
- Esto captura todos los leads de la agencia anterior también

---

## UTM STRUCTURE

Agregar a cada ad:
```
?utm_source=meta&utm_medium=paid&utm_campaign=mayo26&utm_content=[NOMBRE_AD]
```

---
---

# CAMPAÑA 1 — DEPTOS E INVERSIÓN
**`AV_C1_Deptos_Mayo26` · $600**

**Lógica del mes:**
- Días 1-6: testeo con Garibaldi 431 (5 sets × $10/día = $300)
- Día 7+: apagar 3 sets caros, escalar 2 ganadores + abrir San Lorenzo (otros 2 sets × $10/día × 20 días ≈ $300... acá podés ajustar presupuesto según performance)

**Configuración de campaña:**

| Campo | Valor |
|---|---|
| Objetivo | Leads |
| Special Ad Category | **Vivienda** |
| A/B Test | OFF |
| Advanced campaign budget | OFF |
| Performance goal todos los sets | **Maximize conversion leads** |
| Audiencia | Lookalike 1% Argentina |
| Ubicación | Tandil 20km + CABA + GBA |
| Edad/Género | No tocar |
| Placements | Advantage+ |

---

### FASE TESTEO — 5 AD SETS GARIBALDI 431
*$10/día cada uno. Correr hasta gastar $300. Ganadores = sets con menor CPL.*

**AD SET 1 — `GAR431_Rendimiento`**

> Un departamento en el centro de Tandil alquila hoy desde $350.000 por mes.
>
> Garibaldi 431: 1 ambiente, 48 m², frente, USD 110.000.
>
> Hacé los números. Te mandamos toda la info.

Título: `Garibaldi 431 — ¿Cuánto rinde?` · UTM: `gar431_rendimiento`

---

**AD SET 2 — `GAR431_Escasez`**

> Departamento en Garibaldi 431, Tandil.
> 1 ambiente · 48 m² · frente · USD 110.000
>
> Última unidad disponible en este edificio. Centro, entrega inmediata.

Título: `Garibaldi 431 — Última unidad` · UTM: `gar431_escasez`

---

**AD SET 3 — `GAR431_Ciudad`**

> 5.8 personas nuevas por día eligen Tandil. El metro cuadrado subió y sigue subiendo.
>
> Garibaldi 431: USD 110.000 en el centro. Listo para alquilar o para vivir.

Título: `Tandil crece — Tu propiedad en el centro` · UTM: `gar431_ciudad`

---

**AD SET 4 — `GAR431_Objecion`**

> "¿Conviene comprar con esta economía?"
>
> El dólar sube. El alquiler sube. El ladrillo sube.
> Lo que no sube: tu poder de compra si esperás.
>
> Garibaldi 431 · 1 amb · USD 110.000 · Centro de Tandil.

Título: `La respuesta que nadie te da` · UTM: `gar431_objecion`

---

**AD SET 5 — `GAR431_UGC`**

*Video de Santi a cámara, 30-45 seg, estilo orgánico.*

Guión:
> "Te muestro el departamento que más me preguntan esta semana. Garibaldi 431, pleno centro de Tandil. Un ambiente, 48 metros, frente. USD 110.000. Alquila desde $350.000 por mes. Si tenés los dólares y estás mirando dónde ponerlos, escribime."

Título: `Garibaldi 431 — Mirá esto` · UTM: `gar431_ugc`

---

### FASE ESCALA — 2 AD SETS (desde día 7)
*Los 2 ángulos ganadores del testeo, aplicados a la cartera de deptos.*

**AD SET 6 — `Deptos_Inversion`**

> En Tandil hay departamentos desde USD 60.000 que alquilan desde $350.000 por mes.
>
> Tenemos 15+ unidades disponibles — 1 y 2 ambientes.
>
> Si tenés dólares y querés que trabajen, te mandamos las opciones.

Título: `Deptos en Tandil — Desde USD 60.000` · UTM: `deptos_inversion`

---

**AD SET 7 — `SanLorenzo_Stock`**

> San Lorenzo 420, Tandil.
> 2 ambientes · 77 m² · frente · USD 175.000
> 1 ambiente · 54 m² · USD 120.000
>
> 5 unidades disponibles. Entrega inmediata.

Título: `San Lorenzo 420 — 5 unidades` · UTM: `sanlor420_stock`

---

### FORMULARIO C1
**Nombre:** `Form_Deptos_Mayo26` · Form type: **More volume**

**P1:** ¿Buscás para...?
| Respuesta | Acción |
|---|---|
| Invertir / alquilar | → P2 |
| Vivir en ella | → P2 |
| Solo mirando | → **Cerrar** |

**P2:** ¿En qué plazo?
| Respuesta | Acción |
|---|---|
| Próximos 3 meses | → P3 |
| 3 a 12 meses | → P3 |
| Sin fecha | → **Cerrar** |

**P3:** ¿Presupuesto?
| Respuesta | Acción |
|---|---|
| Hasta USD 80.000 | → Submit |
| USD 80.000 – 150.000 | → Submit |
| USD 150.000 – 200.000 | → Submit |
| Prefiero hablarlo | → Submit |

**Thank you:** *Te contactamos a la brevedad. WhatsApp: wa.me/5492494209464*

---
---

# CAMPAÑA 2 — CASAS, PREMIUM Y RETARGETING
**`AV_C2_Casas_Mayo26` · $400**

**Lógica del mes:**
- 2 ad sets adquisición × $10/día × 30 días = $600... ajustar a $7/día = $420 ✓
- 1 ad set retargeting × $5/día × 30 días = $150
- Total: ~$420 + ~$150 = ~$570 → acá ajustás día a día según lo que más performa

**Configuración de campaña:**

| Campo | Valor |
|---|---|
| Objetivo | Leads |
| Special Ad Category | **Vivienda** |
| Performance goal adquisición | **Maximize conversion leads** |
| Performance goal retargeting | **Maximize number of leads** |
| Audiencia adquisición | Lookalike 2% Argentina |
| Audiencia retargeting | Custom Audience 180 días |
| Ubicación | Tandil 20km + CABA + GBA |

---

### AD SET 1 — `Casas_CABA` (adquisición)

> 450 m², 3 dormitorios, jardín y garage. En Tandil. USD 275.000.
>
> El equivalente a un 2 ambientes chico en Palermo.
>
> Sierras, gastronomía, UNICEN. La ciudad que 5.8 personas eligen cada día.

Título: `Tandil: más espacio, misma inversión` · UTM: `casas_caba`

---

### AD SET 2 — `CasaBelgrano_Directa` (adquisición)

> Casa en Belgrano 146, Tandil.
> 4 dormitorios · 3 baños · 200 m² · USD 195.000
>
> Amplia, bien ubicada, lista para entrar.

Título: `Casa Belgrano 146 — Consultas abiertas` · UTM: `belgrano146_directa`

---

### AD SET 3 — `Hammerdem_Retargeting` (180 días)
*Audiencia: todos los que ya interactuaron. Alta frecuencia. Objetivo: reconvertir.*

3 piezas en rotación dentro del mismo ad set:

**Pieza A — Testimonio:**
> "Un cliente nuestro compró en Tandil en 2024. Hoy alquila a $420.000 por mes. Me escribió la semana pasada para agradecerme."
> UTM: `retarg_testimonio`

**Pieza B — Objeción:**
> "¿Y si no consigo inquilino en Tandil?"
> 30% de los hogares alquilan. La demanda supera la oferta hace años. El riesgo real es esperar y que el precio suba.
> UTM: `retarg_objecion`

**Pieza C — Prueba social:**
> Seguimos cerrando operaciones en Tandil. Si estuviste mirando y no tomaste una decisión — este es un buen momento para hablar.
> UTM: `retarg_pruebasocial`

---

### FORMULARIO C2
**Nombre:** `Form_Casas_Mayo26` · Form type: **More volume**

**P1:** ¿Qué tipo de propiedad buscás?
| Respuesta | Acción |
|---|---|
| Casa | → P2 |
| Departamento grande (+$200k) | → P2 |
| Lote para construir | → P2 |
| Solo mirando | → **Cerrar** |

**P2:** ¿En qué plazo?
| Respuesta | Acción |
|---|---|
| Próximos 3 meses | → P3 |
| 3 a 12 meses | → P3 |
| Sin fecha | → **Cerrar** |

**P3:** ¿Presupuesto?
| Respuesta | Acción |
|---|---|
| USD 90.000 – 200.000 | → Submit |
| USD 200.000 – 300.000 | → Submit |
| Más de USD 300.000 | → Submit |
| Prefiero hablarlo | → Submit |

**Thank you:** *Te contactamos a la brevedad. WhatsApp: wa.me/5492494209464*

---
---

## TIMELINE

| Día | Acción |
|---|---|
| **Hoy** | Crear Custom Audience + Lookalike + Retargeting 180d |
| **Hoy** | Lanzar C1 (5 sets Garibaldi) + C2 (2 adquisición + 1 retargeting) |
| **Día 6-7** | Revisar C1: apagar 3 sets más caros, quedar con 2 ganadores |
| **Día 7** | Lanzar ad sets 6 y 7 de C1 (San Lorenzo + Deptos general) |
| **Día 15** | Revisión: reasignar presupuesto hacia lo que mejor CPL tenga |
| **Día 30** | Análisis: CPL, leads calificados, visitas, cierres por campaña y UTM |

---

## CONTENIDO URGENTE

| Pieza | Campaña | Para cuándo |
|---|---|---|
| Video Santi — Garibaldi 431 (guión arriba en AD SET 5) | C1 | 🔴 Hoy |
| 4 fotos Garibaldi 431 | C1 | 🔴 Hoy |
| 4 fotos Casa Belgrano 146 | C2 | 🟡 Antes día 7 |
| 4 fotos San Lorenzo 420 | C1 | 🟡 Antes día 7 |
| Video objeción "¿Y si no consigo inquilino?" | C2 Retargeting | 🟡 Esta semana |
| Video/foto testimonio cliente real | C2 Retargeting | 🟡 Esta semana |

---

## CHECKLIST LANZAMIENTO

- [ ] Base de datos exportada → Custom Audience creada en Meta
- [ ] Lookalike 1% Argentina creado
- [ ] Audiencia retargeting 180 días creada
- [ ] Video Santi a cámara (Garibaldi) listo
- [ ] Fotos Garibaldi 431 (4+)
- [ ] C1 creada con Special Ad Category: Vivienda
- [ ] C2 creada con Special Ad Category: Vivienda
- [ ] Formularios con conditional logic configurados y testeados
- [ ] UTMs en todos los ads
- [ ] Performance goal: Maximize conversion leads (adquisición)
- [ ] Bot de WhatsApp activo

---

*Fuentes: Reunión Leonel Paez 02/05/2026 · YouTube Brain LeadDex 5/5 · Cristina Meta Ads 4/5*
