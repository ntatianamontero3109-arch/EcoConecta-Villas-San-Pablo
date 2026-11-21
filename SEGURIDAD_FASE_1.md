# EcoConecta 2.0 — Fase 1: seguridad

## Alcance
- No se ejecutaron migraciones ni operaciones contra PostgreSQL.
- No se modificaron usuarios, solicitudes, puntos ni evidencias existentes.
- Se eliminó `.env` del paquete de entrega; contiene secretos locales.
- La configuración ahora exige `SECRET_KEY` con mínimo 32 caracteres y rechaza claves de ejemplo.
- Docker Compose exige `POSTGRES_PASSWORD` explícita.
- La carga de evidencias se limita por bloques a 8 MiB y valida firmas básicas JPEG/PNG/WEBP.
- El cierre de recolección bloquea la fila de solicitud durante la transacción para reducir el riesgo de acreditación concurrente duplicada.

## Instalación segura
1. Mantén detenida la instalación solo si necesitas actualizar sus archivos; no borres volúmenes Docker.
2. Conserva tu `.env` local existente fuera del ZIP. No lo compartas ni lo subas a Git.
3. Comprueba que `SECRET_KEY` tenga al menos 32 caracteres aleatorios y que `POSTGRES_PASSWORD` coincida con la contraseña ya configurada para el volumen PostgreSQL existente.
4. Comprueba que `DATABASE_URL` use el servicio `db` y la misma contraseña de PostgreSQL.
5. No cambies `POSTGRES_USER`, `POSTGRES_DB` ni el nombre del volumen `postgres_data` en una instalación con datos existentes.
6. Ejecuta `docker compose config` para validar la configuración antes de reiniciar.
7. Después de reemplazar archivos, ejecuta `docker compose up --build -d` y revisa `docker compose ps` y `docker compose logs --tail=100 web`.

## Importante sobre secretos
Si los secretos del `.env` anterior se compartieron o quedaron expuestos, rota `SECRET_KEY` y las credenciales externas. Cambiar `SECRET_KEY` invalida los tokens de sesión existentes, por lo que los usuarios deberán iniciar sesión de nuevo.

## Limitaciones pendientes
Esta fase no incorpora todavía Alembic, registro de movimientos de puntos, limitación de intentos de login, cookies seguras, CSP, escaneo antivirus, pruebas automatizadas completas ni despliegue de producción. Deben abordarse antes de declarar el sistema listo para producción.
