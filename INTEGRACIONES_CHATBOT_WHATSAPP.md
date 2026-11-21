# Integraciones de EcoConecta 2.0.1 — modo gratuito

## EcoBot local (sin API de pago)

El endpoint `POST /api/chat` recibe preguntas libres y hasta 12 mensajes de conversación. La respuesta se genera en el propio backend con una base de conocimientos local y puntuación léxica/contextual. No requiere `OPENAI_API_KEY`, créditos, tarjeta ni conexión a un proveedor de IA.

EcoBot cubre uso de la plataforma, registro, solicitudes, estados, horarios (sin inventar calendarios), separación, orgánicos, reciclables, papel/cartón, plásticos, vidrio, metales, residuos especiales, puntos, roles, privacidad y notificaciones. Si no encuentra una respuesta con suficiente coincidencia, lo indica y solicita aclaración; no inventa estados, cobertura, horarios, premios ni datos personales. La conversación se conserva en memoria de la pestaña del navegador y se envía al servidor para interpretar preguntas de seguimiento.

**Límite funcional honesto:** esta versión no es un modelo generativo y no puede responder de manera fiable cualquier pregunta arbitraria o ajena a su base de conocimiento. Para respuestas generativas abiertas se necesitaría ejecutar un modelo local (hardware/descarga) o contratar una API externa.

## WhatsApp: preparado, desactivado por defecto

Las notificaciones internas de la plataforma sí se crean automáticamente para coordinadores, recolectores y ciudadanos según los eventos y roles. La integración de WhatsApp Cloud API permanece en el código como opción, pero `WHATSAPP_ENABLED=false` por defecto. No se envían mensajes a WhatsApp ni se generan cargos en el modo gratuito.

Para activar WhatsApp más adelante se requiere un portafolio Meta, aplicación de desarrollador, cuenta y número de WhatsApp Business Platform, token, identificador del número, consentimiento de los destinatarios y revisión de las tarifas/plantillas vigentes. Los mensajes proactivos normalmente requieren plantillas aprobadas. No se debe activar sin revisar previamente los costos aplicables.

Variables opcionales (mantener vacías mientras no se autorice la integración):

```env
WHATSAPP_ENABLED=false
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_API_VERSION=
WHATSAPP_TEMPLATE_NAME=
WHATSAPP_TEMPLATE_LANGUAGE=es_CO
```

## Acceso por perfiles

- Visitante: abre `/`, ve información pública y puede usar EcoBot sin iniciar sesión.
- Ciudadano: se registra o inicia sesión para crear solicitudes, consultar historial y puntos propios.
- Coordinación orgánica: gestiona únicamente el flujo orgánico y sus recolectores.
- Coordinación reciclaje: gestiona únicamente el flujo reciclable y sus recolectores.
- Recolector: consulta solicitudes asignadas a su usuario y registra avances/evidencias.
- Administrador: consulta y gestiona globalmente ambos flujos.

La interfaz adapta la navegación al rol, pero la autorización efectiva se verifica en el backend. El registro público solo crea cuentas `community`; no permite autoseleccionar roles internos.
