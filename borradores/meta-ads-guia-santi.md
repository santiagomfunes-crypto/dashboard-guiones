# Guía de Configuración — Santi
## Meta Ads Manager · Campaña Mayo 2026

*Seguir en orden. No saltear pasos.*

---

## PASO 1 — AUDIENCIAS (hacer primero, antes de crear campañas)

### A. Subir base de datos
1. Pedirle a Santiago el archivo de contactos (mails + teléfonos)
2. Meta Business → Audiences → **Create Audience** → Custom Audience
3. Seleccionar: **Customer list**
4. Subir el CSV. Esperar que Meta procese (puede tardar hasta 1 hora)

### B. Crear Lookalike
1. Audiences → **Create Audience** → Lookalike Audience
2. Source: la Custom Audience recién creada
3. Audience location: **Argentina**
4. Audience size: **1%**
5. Guardar como: `Lookalike 1% AR — Base Clientes`

### C. Crear audiencia retargeting
1. Audiences → **Create Audience** → Custom Audience → **Meta sources**
2. Tildar: Instagram account + Facebook page + Lead form
3. Período: **180 días**
4. Guardar como: `Retargeting 180d — Interacciones`

---

## PASO 2 — CAMPAÑA 1 ($600)

### Crear la campaña
1. Ads Manager → **+ Create**
2. Objetivo: **Leads**
3. Campaign name: `AV_C1_Deptos_Mayo26`
4. Special ad categories: tildar **Housing** (Vivienda)
5. A/B test: OFF
6. Campaign budget optimization: OFF
7. → **Next**

### Crear Ad Set 1 (repetir estructura para los 5)
1. Ad set name: `GAR431_Rendimiento`
2. Conversion location: **Website** → seleccionar el Pixel
   - Si no hay pixel: seleccionar **Instant forms**
3. Performance goal: **Maximize number of conversion leads** ← importante, no el default
4. Facebook page: Grupo Alta Vista Otero
5. Budget: **$10 daily**
6. Audience: seleccionar `Lookalike 1% AR — Base Clientes`
7. Locations: agregar **Tandil** (20km) + **Buenos Aires** (ciudad) + **Gran Buenos Aires**
8. Age/Gender: **no tocar** (categoría vivienda no lo permite)
9. Placements: **Advantage+ placements** (dejar automático)
10. → **Next**

### Crear el Ad
1. Ad name: `GAR431_Rendimiento_V1`
2. Identity: página de Facebook + Instagram
3. Format: **Single image or video**
4. Subir foto: exterior del edificio Garibaldi 431
5. Primary text: pegar el texto del Ad Set 1 (ver campaña completa)
6. Headline: `Garibaldi 431 — ¿Cuánto rinde?`
7. Call to action: **More information** (Más información)
8. Destination: link al formulario (ver abajo cómo crear el form)
9. Repetir con 3 fotos más → 4 ads por set

### Crear el formulario (una sola vez, usar en los 5 sets)
1. En el ad, destination → **Instant form** → **+ Create form**
2. Form name: `Form_Deptos_Mayo26`
3. Form type: **More volume**
4. Intro: usar foto del depto, headline = `Propiedades en Tandil`
5. Questions → agregar preguntas:
   - Multiple choice: "¿Buscás para...?" (opciones: Invertir/alquilar · Vivir · Solo mirando)
   - Multiple choice: "¿En qué plazo?" (opciones: 3 meses · 3-12 meses · Sin fecha)
   - Multiple choice: "¿Presupuesto?" (opciones: Hasta $80k · $80-150k · $150-200k · Prefiero hablarlo)
6. Conditional logic: activar
   - "Solo mirando" → End form (not a lead)
   - "Sin fecha" → End form (not a lead)
   - Todo lo demás → Submit form
7. Contact fields: Full name + Email + Phone number
8. Privacy policy: `propiedades.santiagofunes.com.ar`
9. Thank you screen:
   - Headline: `¡Gracias!`
   - Description: `Te contactamos a la brevedad. También podés escribirnos directo.`
   - CTA button: `Escribir por WhatsApp`
   - Link: `https://wa.me/5492494209464`
10. → **Save**

### Duplicar para los otros 4 ad sets
1. Seleccionar Ad Set 1 → **Duplicate**
2. Cambiar: nombre del ad set, texto del ad, headline, UTM
3. El formulario es el mismo — no duplicar, reutilizar

---

## PASO 3 — CAMPAÑA 2 ($400)

### Crear la campaña
1. → **+ Create**
2. Objetivo: **Leads**
3. Campaign name: `AV_C2_Casas_Mayo26`
4. Special ad categories: **Housing**
5. → **Next**

### Ad Set Adquisición (2 sets)
- Mismo proceso que C1
- Audiencia: `Lookalike 1% AR — Base Clientes`
- Budget: **$7/día**
- Sets: `Casas_CABA` y `CasaBelgrano_Directa`
- Formulario: crear `Form_Casas_Mayo26` (mismo proceso, preguntas adaptadas)

### Ad Set Retargeting — Hammerdem (1 set)
- Nombre: `Hammerdem_Retargeting`
- Audiencia: `Retargeting 180d — Interacciones` ← la que creaste en Paso 1C
- Performance goal: **Maximize number of leads** (este sí, no el de conversion)
- Budget: **$5/día**
- Subir 3 creativos: testimonio + objeción + prueba social
- No necesita formulario con conditional logic — form simple

---

## PASO 4 — REVISIÓN DÍA 6-7

Entrar a Ads Manager → ver columna **Cost per result** de cada ad set de C1.

Ordenar de menor a mayor CPL. Los 3 con mayor CPL → **desactivar**.
Los 2 con menor CPL → **mantener y lanzar ad sets 6 y 7** (Deptos general + San Lorenzo).

---

## CHECKLIST FINAL ANTES DE PUBLICAR

- [ ] 4 audiencias creadas: Lookalike 1% + Retargeting 180d
- [ ] C1 creada con Special Ad Category: Housing
- [ ] C2 creada con Special Ad Category: Housing
- [ ] Formularios con conditional logic guardados y previsualizados
- [ ] Thank you page botón apunta a wa.me/5492494209464
- [ ] Performance goal adquisición = **Maximize conversion leads**
- [ ] Performance goal retargeting = **Maximize number of leads**
- [ ] Fotos Garibaldi 431 subidas (mínimo 4)
- [ ] Video Santi (Garibaldi UGC) subido
- [ ] → **Publish** en ambas campañas

---

*Dudas → Santiago o revisar el doc completo en borradores/meta-ads-mayo2026.md*
