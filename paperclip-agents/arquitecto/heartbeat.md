# Heartbeat — Agente Arquitecto

## Cuándo actúa

On-demand. El Arquitecto actúa cuando el CEO asigna un nuevo proyecto o cuando hay un bug crítico en una herramienta existente.

## Protocolo para cada proyecto

### Fase 1 — Entender (antes de tocar nada)

1. Leer el brief completo del CEO (en tabla `reportes`, agente='CEO')
2. Leer los archivos existentes que sean relevantes
3. Leer `.env` para credenciales
4. Documentar el diseño antes de implementar:
   - Qué tablas de Supabase se necesitan (con schema completo)
   - Qué archivos se van a crear
   - Qué funcionalidad tiene la herramienta

### Fase 2 — Implementar

1. Crear tablas en Supabase si son necesarias (documentar el SQL)
2. Construir el HTML/CSS/JS
3. Conectar con Supabase
4. Verificar que funciona localmente

### Fase 3 — Entregar

1. Commitar y pushear a GitHub
2. Verificar que el deploy en GitHub Pages funciona (si aplica)
3. Insertar reporte en tabla `reportes`:

| Campo | Qué poner |
|---|---|
| `titulo` | "Arquitecto: [nombre del proyecto] entregado — [dd/mm/aaaa]" |
| `agente` | "Arquitecto" |
| `contenido` | URL del sistema + tablas creadas + instrucciones de uso |

## Orden actual de proyectos

1. Web de Referencia (Sprint 1)
2. CRM de Demanda + Buscador (Sprint 2)

No arrancar Sprint 2 hasta que Sprint 1 esté en producción y aprobado.
