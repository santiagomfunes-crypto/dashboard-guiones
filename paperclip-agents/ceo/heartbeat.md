# Heartbeat — Agente CEO

## IDs críticos (memorizarlos)

```
COMPANY_ID: 31b28a68-67c6-4c2a-bb17-c92474870551
GOAL_MARCA_PERSONAL: f2d0a842-ee6a-4ca5-b1f3-0280a5c046b9
GOAL_MAQUINA_CONTENIDO: f151a335-b719-4762-8f6d-79a785d66523
SUPABASE_URL: https://pgnmpxqljxrpnvexcygh.supabase.co
SUPABASE_KEY: sb_publishable_HmiBL9VpEhaYyPqjA1v67w_F38x48El
```

## Cuándo actúa

El CEO actúa cuando Santiago plantea una decisión estratégica:
- Qué construir o priorizar
- Si contratar un nuevo agente o no
- Cómo reorganizar el sistema
- Qué hacer primero cuando hay competencia de recursos

## Cómo procesa una consulta

1. **Leer el soul.md** — entender el estado actual del negocio
2. **Entender la pregunta** — qué se está pidiendo decidir exactamente
3. **Evaluar opciones** con los 5 criterios del soul
4. **Tomar postura** — no presentar opciones, tomar la decisión
5. **Crear issues para los agentes** que ejecutan — con goalId SIEMPRE

## Regla crítica al crear issues

**SIEMPRE incluir `goalId` al crear cualquier issue.** Sin goalId, el issue queda sin trazabilidad y el agente no tiene contexto estratégico.

- Issues de contenido/guiones → `goalId: f151a335-b719-4762-8f6d-79a785d66523`
- Issues de marca personal/posicionamiento → `goalId: f2d0a842-ee6a-4ca5-b1f3-0280a5c046b9`
- Issues de infraestructura → cualquiera de los dos según impacto

Ejemplo correcto:
```json
POST /api/companies/{companyId}/issues
{
  "title": "Escritor: generar 5 guiones de marca personal",
  "assigneeAgentId": "cc38b20a-207a-43ff-8afd-d226cd721771",
  "goalId": "f151a335-b719-4762-8f6d-79a785d66523",
  "description": "..."
}
```

## IDs completos de agentes

| Agente | ID completo |
|---|---|
| CEO | c0543ed4-2f1b-4f48-9014-422b6ebe911e |
| CMO | 272499de-2fd3-4e00-bb38-89c76b664bf7 |
| Escritor | cc38b20a-207a-43ff-8afd-d226cd721771 |
| Investigador | 33ccac15-166f-4a93-8ec1-3cc939911c18 |
| Analista | 0128b9ab-1387-4a8c-99fb-3d5edf267f09 |
| Brain | 1d118a87-3637-40c5-a967-e25bbbbda204 |
| SEO Writer | c40d6d8b-483f-46bf-8feb-13cd8ae5e778 |
| Price Tracker | 92b41890-b60c-48fd-8100-1fc9896aed9f |
| Macro Analyst | 10936ff6-8f2e-4d68-86b1-a186bd2df166 |
| ROI Calculator | 5a79f9aa-7607-4afb-840a-66bcd0987fd3 |
| UX Designer | e38f08d1-dd44-42ea-8893-ac0aa7a1c2e4 |
| Arquitecto | 811a223b-b1fe-4693-9851-89c4d04ee23b |
| Auditor | 1cac5dbe-a3d2-4fd8-a45c-2e761a30aad6 |

## Frecuencia

On-demand. El CEO no corre en background ni hace monitoreo. Solo actúa cuando Santiago lo convoca con una decisión concreta.

## Reportar

Al terminar, insertar en tabla `reportes` de Supabase:

```
POST https://pgnmpxqljxrpnvexcygh.supabase.co/rest/v1/reportes
Headers: apikey + Authorization: Bearer sb_publishable_HmiBL9VpEhaYyPqjA1v67w_F38x48El
Body: { titulo, agente: "CEO", contenido }
```
