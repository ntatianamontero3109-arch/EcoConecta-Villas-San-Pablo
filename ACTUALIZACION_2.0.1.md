# EcoConecta 2.0.1 — actualización controlada en modo gratuito

## Cambios incluidos
- Asistente EcoBot de preguntas abiertas con base de conocimiento local y seguimiento contextual básico; no requiere OpenAI API, créditos ni tarjeta.
- Respuestas prudentes: no inventa horarios, cobertura, estados privados, puntos oficiales ni datos de cuenta; deriva cuando no tiene información suficiente.
- Notificaciones internas para ciudadanos, coordinadores y recolectores según el flujo y el estado.
- Integración WhatsApp Cloud API conservada como módulo opcional, desactivado por defecto mediante `WHATSAPP_ENABLED=false`; no se envían mensajes externos ni se generan cargos en el modo gratuito.
- Separación de vistas por rol y autorización validada en backend.
- Alta local segura de cuentas internas mediante `scripts/create_staff.py`; el registro público solo crea ciudadanos.
- Pruebas automatizadas del motor local del chatbot.
- No se agregan tablas ni se ejecutan migraciones de PostgreSQL.

## Instalación conservando datos
1. Extrae este ZIP sobre la carpeta de trabajo existente. El paquete no contiene `.env`, `.git`, `uploads` ni respaldos de base de datos.
2. Conserva tu `.env` actual. No lo reemplaces por `.env.example`.
3. Ejecuta `.\INSTALAR_MODO_GRATUITO.ps1` desde PowerShell en la carpeta del proyecto.
4. El script valida Compose, PostgreSQL y los volúmenes `ecoconecta_postgres_data` y `ecoconecta_uploads_data`.
5. Reconstruye solamente el servicio `web`; no detiene ni elimina PostgreSQL ni volúmenes.
6. Comprueba `http://localhost:8000`, `/api/health` y `/docs`.
7. Ejecuta `.\VERIFICAR_ECOCONECTA.ps1` para pruebas de humo del frontend y EcoBot.

No ejecutes `docker compose down -v`, `docker volume rm`, `docker system prune --volumes` ni reinicialices la base de datos.

## Límites conocidos
- EcoBot es un motor local basado en conocimiento y coincidencia contextual; no es un modelo generativo y no puede garantizar respuesta correcta a cualquier pregunta arbitraria. La base de conocimiento puede ampliarse sin pagar API.
- WhatsApp automático está preparado pero desactivado. Para mensajes externos se requiere configuración oficial de Meta, consentimiento, plantillas y revisión de costos vigentes.
- Las notificaciones internas requieren que el usuario inicie sesión y consulte el panel; esta entrega no incluye push móvil cuando el navegador está cerrado.
- Antes de producción se requiere HTTPS, política de privacidad, respaldo restaurable, recuperación de contraseña, migraciones formales, monitoreo y pruebas externas de seguridad.
