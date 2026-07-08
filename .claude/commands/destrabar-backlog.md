---
description: Loop de objetivo — destraba el backlog de guiones "listo" hasta llenar una shortlist verificada de "filmá primero"
argument-hint: "[N-guiones-objetivo, default 8]"
allowed-tools: Read, Bash, Grep, Glob, Agent
---

# Objetivo: destrabar el backlog de guiones "listo"

Este es un **loop de objetivo** (goal-based, no turn-based): iterá hasta cumplir el
criterio de salida cuantitativo de abajo, después parás y reportás. No es "mejorá un
poco los guiones" — es llegar a un número concreto de guiones verificados listos para grabar.

Meta: **N = ${1:-8}** guiones del backlog `status='listo'` con veredicto ✅ del
`verificador`, ordenados por prioridad de filmación.

## Criterio de salida (deterministico — parás cuando se cumple)

Terminás cuando **ambas** condiciones son verdad:
1. Tenés **N guiones con veredicto `✅ LISTO`** del agente `verificador`
   (Agent tool, `subagent_type: verificador`), cada uno con score completo (todo 2, sin red flags).
2. Cada 🟡/🔴 que encontraste en el camino quedó **reclasificado**: 🟡 con su fix anotado,
   🔴 marcado como candidato a `descartado` o a reescritura E1/E2/E5.

Tope de seguridad: si tras **15 pasadas por verificador** no juntaste N ✅, parás igual y
reportás cuántos ✅ lograste + por qué el backlog no da para más (patrón de falla dominante).

## Loop

0. Cargá el contexto del skill `escritor-sfre` (Step 0): brand-context, voz-santiago,
   framework-angulos, datos-tandil. GIGO — sin esto el verificador no tiene criterio.
1. Bajá el backlog `status='listo'` de Supabase vía REST (paginar de a 1000; anon key):
   `select=id,titulo,angulo,hook,texto,status,created_at&status=eq.listo&order=created_at.desc`.
   Usá `$SUPABASE_URL` y `$SUPABASE_ANON_KEY` — nunca hardcodear.
2. Priorizá candidatos: los de ángulo/enfoque que **sí se filma** (Tandil creciendo +
   seguridad/desarrollo, E1/E2/E5). Descartá de entrada los que tengan datos quemados como hook.
3. Pasá cada candidato por `verificador` (SOLO el texto, sin tu razonamiento). Acumulá los ✅.
4. Un 🟡 con fix barato: aplicá el fix y volvé a pasarlo UNA vez. Si sigue 🟡/🔴, va a la
   pila de reclasificación, no a la shortlist.
5. Repetí 3-4 hasta cumplir el criterio de salida o tocar el tope de 15 pasadas.

## Salida (cuando parás)

- **`## Filmá primero`** — la shortlist de N ✅: `guion | ángulo/enfoque | por qué performa`.
- **`## Reclasificar`** — los 🟡 (con fix) y 🔴 (descartar/reescribir).
- **`## Patrón de falla`** — el motivo #1 por el que este backlog no se filmaba. Si es
  estructural (todos comp/prod sin historia, tono turístico recurrente), decilo y proponé
  **arreglar el sistema** (`referencia/arreglar-el-sistema.md`), no solo estos guiones.

No escribas guiones nuevos: el objetivo es stock existente. No marques nada `filmado`.
