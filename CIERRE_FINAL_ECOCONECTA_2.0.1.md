# EcoConecta 2.0.1 — Paquete de cierre

## Incluido

- Portal público y vista de ciudadano: registro, inicio de sesión, solicitudes, seguimiento, historial, puntos y notificaciones propias.
- Panel operativo diferenciado por rol: administración global, coordinación orgánica, coordinación de reciclaje, recolector orgánico y recolector de reciclaje.
- Autorización en backend por rol y por solicitud; el registro público únicamente crea cuentas `community`.
- Notificaciones internas para responsables del flujo, recolectores asignados, ciudadano y administradores en los eventos principales.
- EcoBot local, sin API externa ni consumo de servicios de IA pagos. Reconoce preguntas sobre solicitudes, materiales, puntos, seguimiento y horarios; para datos personales remite al panel autenticado y para información desconocida no inventa.
- WhatsApp Cloud API opcional y desactivada por defecto. Los envíos requieren configuración oficial, destinatarios autorizados explícitamente y consentimiento. WhatsApp Business Platform no puede garantizarse gratis ni ilimitado.
- Docker Compose, PostgreSQL, almacenamiento de evidencias y documentación.

## Corrección de EcoBot

Se incorporó clasificación determinista para expresiones de seguimiento como “¿Cómo consulto mi solicitud?”, “¿Dónde veo mi solicitud?”, “¿Ya recogieron mis residuos?” y “¿Cómo va mi pedido?”, evitando que se clasifiquen como consultas de horario. Las preguntas de horarios siguen diferenciándose.

## Verificaciones ejecutadas sobre el paquete

- `python -m compileall -q app scripts tests`: correcto.
- `python -m unittest discover -s tests -v`: 10 pruebas aprobadas (incluye retrasos de recolección y consulta de materiales).
- `python -m py_compile app/*.py`: correcto.
- `node --check app/static/app.js`: correcto.
- Se inspeccionó el frontend y se confirmó que contiene vistas de comunidad y panel operativo con rótulos por rol.
- Se reforzaron reglas de asignación, programación, avance, cancelación y cierre por flujo y usuario asignado.
- Se agregó gestión administrativa protegida de roles y estado de cuentas, con protección del último administrador activo.
- La API de salud comprueba PostgreSQL y las respuestas JSON declaran UTF-8.
- Se inspeccionó el backend y se confirmó filtrado de solicitudes por rol, control de acceso a solicitudes, notificaciones internas y registro público restringido al rol ciudadano.

## Límites de validación

Las pruebas unitarias, compilación Python y sintaxis JavaScript se ejecutaron sobre este paquete. No se ha ejecutado contra la instancia PostgreSQL del usuario ni se han probado sesiones reales de sus seis perfiles. Esas pruebas requieren acceso a su entorno y credenciales locales, que no se incluyen. El estado de API/contendedores que el usuario reportó previamente no equivale a una prueba integral de cada flujo.

## Protección de datos

No se incluye `.env`, contraseñas, tokens, datos de usuarios ni volúmenes. Conservar el `.env` existente y los volúmenes Docker existentes. No ejecutar `docker compose down -v` ni `docker volume rm`.
