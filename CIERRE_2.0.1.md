# EcoConecta 2.0.1 - Ajustes de cierre

## Cambios incluidos en esta actualización

- El administrador activo recibe notificaciones internas globales cuando se registra, asigna, programa, avanza, finaliza o cancela una solicitud.
- Los coordinadores continúan recibiendo alertas del flujo que les corresponde.
- Los ciudadanos pueden consultar y marcar como leídas sus propias notificaciones desde la sección "Mis solicitudes".
- La lista de recolectores excluye cuentas deshabilitadas.
- No se envían mensajes de WhatsApp a números que no estén expresamente incluidos en `WHATSAPP_ALLOWED_RECIPIENTS`.
- La consulta y modificación de notificaciones sigue limitada al usuario propietario.
- No se agregan ni eliminan tablas; no se modifica el esquema de PostgreSQL.
- Se conserva el modo gratuito local de EcoBot.

## Límites conocidos que deben comunicarse con claridad

- EcoBot usa una base de conocimientos local, coincidencia semántica ligera, sinónimos y contexto corto. Puede contestar preguntas formuladas libremente dentro de los temas que conoce, pero no es un modelo generativo y no puede garantizar respuestas a cualquier pregunta.
- La integración de WhatsApp requiere credenciales válidas de Meta/WhatsApp Cloud API, plantillas aprobadas cuando corresponda, habilitación expresa y consentimiento. No es una integración gratuita ilimitada. Con la configuración vacía permanece desactivada.
- Esta actualización no publica el proyecto en GitHub ni configura un hosting público.

## Instalación

1. Extraer el ZIP en una carpeta nueva.
2. Copiar el `.env` de la instalación existente a esta carpeta (no compartirlo ni subirlo a GitHub).
3. Ejecutar PowerShell en la carpeta extraída.
4. Ejecutar `Set-ExecutionPolicy -Scope Process Bypass`.
5. Ejecutar `.\INSTALAR_MODO_GRATUITO.ps1`.
6. Ejecutar `.\VERIFICAR_ECOCONECTA.ps1`.

El instalador reconstruye únicamente el servicio web. No ejecuta `docker compose down`, no elimina volúmenes y no reinicia PostgreSQL.
