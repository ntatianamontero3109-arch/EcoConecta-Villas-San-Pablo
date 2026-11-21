# EcoConecta 2.0.1 — notas de entrega revisada

## Cambios incluidos en esta revisión

- Panel administrativo con listado y edición de rol/estado de cuentas.
- Protección para conservar al menos un administrador activo y evitar que el administrador se desactive a sí mismo.
- Reglas de autorización reforzadas para coordinadores y recolectores por flujo y asignación.
- Los recolectores no pueden cancelar solicitudes.
- Bloqueo de asignación/programación de solicitudes cerradas o canceladas.
- Validación para impedir programaciones con fecha pasada.
- Avisos de cancelación también al recolector asignado.
- Endpoint de salud con comprobación real de PostgreSQL.
- Respuestas JSON declaradas como UTF-8.
- EcoBot reconoce preguntas sobre recolecciones no atendidas y materiales aceptados.
- Mejoras visuales de consistencia, accesibilidad y adaptación móvil.
- Pruebas unitarias y flujo CI de GitHub Actions.

## Límites que requieren configuración/despliegue

- WhatsApp Business está desactivado hasta disponer de credenciales oficiales, consentimiento de destinatarios y configuración aprobada.
- El repositorio público no equivale a un despliegue público de FastAPI. Para una URL web pública se necesita un servicio de hosting para el backend y PostgreSQL persistente.
- Antes de producción deben realizarse pruebas de aceptación con las cuentas reales de los seis perfiles, HTTPS, copias de seguridad, política de privacidad y revisión de secretos.
- No incluir `.env`, credenciales ni datos reales en GitHub.
