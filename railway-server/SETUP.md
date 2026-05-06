# Setup — Sofía WhatsApp Bot en Railway

## Variables de entorno en Railway

Ir a Railway → tu proyecto → Variables y agregar:

### Ya existentes (verificar que estén)
```
SUPABASE_URL=https://pgnmpxqljxrpnvexcygh.supabase.co
SUPABASE_SERVICE_KEY=...
SFRE_SUPABASE_URL=https://bsvcorcwcijpvwzxjzgu.supabase.co
SFRE_SUPABASE_SERVICE_KEY=...
API_KEY=altavista-n8n-2026
```

### Nuevas — agregar estas
```
ANTHROPIC_API_KEY=sk-ant-...        ← tu key de console.anthropic.com
WHATSAPP_TOKEN=                     ← access token de Meta (paso 3 abajo)
WHATSAPP_PHONE_ID=                  ← phone number ID de Meta (paso 3 abajo)
WHATSAPP_VERIFY_TOKEN=altavista-sofia-2026
SANTIAGO_PHONE=5492494209464        ← tu número para recibir escalaciones (sin +)
```

---

## Pasos para conectar Meta WhatsApp

### 1. Crear app en Meta for Developers
- Ir a https://developers.facebook.com
- "Mis apps" → "Crear app"
- Tipo: "Empresa" → siguiente
- Nombre: "Altavista Sofia" → crear
- En el dashboard de la app: "Agregar productos" → seleccionar **WhatsApp**

### 2. Registrar el número nuevo (la eSIM de Tuenti)
- En la app de Meta: WhatsApp → Configuración de la API
- "Agregar número de teléfono"
- Ingresar el número de Tuenti en formato internacional (+54 9 ...)
- Meta manda un SMS al número → ingresar el código de verificación

### 3. Obtener las credenciales
- **WHATSAPP_TOKEN**: En Meta → WhatsApp → Configuración de la API → "Token de acceso temporal"
  (para producción hay que generar un token permanente via System User)
- **WHATSAPP_PHONE_ID**: mismo lugar, aparece como "ID de número de teléfono"

### 4. Configurar el webhook en Meta
- En Meta → WhatsApp → Configuración → Webhooks
- URL de callback: `https://TU-URL-RAILWAY.up.railway.app/whatsapp/webhook`
- Token de verificación: `altavista-sofia-2026`
- Suscribirse a: **messages**
- Hacer clic en "Verificar y guardar"

### 5. Correr el SQL en Supabase
- Abrir Supabase → proyecto sfre-web (bsvcorcwcijpvwzxjzgu)
- SQL Editor → pegar el contenido de `../sfre-web/supabase/migrations/sofia_chatbot.sql`
- Ejecutar

---

## Probar que funciona

```bash
# Health check
curl https://TU-URL.up.railway.app/health

# Simular mensaje entrante (reemplazar lead_id y phone)
curl -X POST https://TU-URL.up.railway.app/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "5492494000000",
            "type": "text",
            "text": { "body": "Hola, busco una casa en Tandil hasta 100000 dólares" }
          }]
        }
      }]
    }]
  }'
```

---

## Flujo de escalación

Cuando Sofía no puede responder, manda un mensaje a `SANTIAGO_PHONE`:

```
⚠️ Sofía escaló una conversación
Lead: [nombre] (+549...)
Último mensaje: [texto]
Respondele desde tu número si querés tomar el hilo.
```

A partir de ahí vos respondés desde tu número personal directamente al lead.
