# Modelo de datos PostgreSQL

```mermaid
erDiagram
  USERS ||--o{ COLLECTION_REQUESTS : solicita
  USERS o|--o{ COLLECTION_REQUESTS : coordina
  USERS o|--o{ COLLECTION_REQUESTS : recolecta
  COLLECTION_REQUESTS ||--o{ REQUEST_EVENTS : registra
  USERS o|--o{ REQUEST_EVENTS : ejecuta
  USERS {
    int id PK
    varchar full_name
    varchar phone UK
    varchar email UK
    varchar address
    varchar password_hash
    varchar role
    boolean active
    int points
    timestamp created_at
  }
  COLLECTION_REQUESTS {
    int id PK
    varchar code UK
    int user_id FK
    varchar generator_type
    varchar waste_type
    varchar flow
    varchar address
    text notes
    varchar preferred_time
    varchar status
    int coordinator_id FK
    int collector_id FK
    date scheduled_date
    time scheduled_time
    timestamp collected_at
    float weight_kg
    int points_awarded
    timestamp created_at
  }
  REQUEST_EVENTS {
    int id PK
    int request_id FK
    int actor_id FK
    varchar status
    text detail
    timestamp created_at
  }
```

## Diccionario resumido

| Tabla | Propósito | Reglas |
|---|---|---|
| `users` | Identidad, perfil y puntos | Teléfono único; contraseña almacenada como hash |
| `collection_requests` | Solicitud y ciclo operativo | Código único; flujo orgánico o reciclable; estado trazable |
| `request_events` | Auditoría de eventos | Cada cambio operativo registra actor, estado, detalle y fecha |

## Estados del proceso

`recibida` → `asignada` → `programada` → `recolectada`

También puede terminar en `cancelada`. La API impide cerrar una solicitud no programada. La programación registra simultáneamente fecha, hora y recolector.

## Puntos

`puntos = redondear(peso_kg × POINTS_PER_KG)`

`POINTS_PER_KG` es un parámetro técnico demostrativo. Su valor debe ser validado por Fundación Santo Domingo antes de cualquier operación real.


## Actualización 1: seguimiento, evidencias y notificaciones

- `collection_evidence`: relación con `collection_requests` y `users`; almacena material, peso, ruta de fotografía, observaciones y fecha.
- `notifications`: destinatario, solicitud relacionada, título, mensaje, estado de lectura y fecha.
- `request_events`: registra cada transición de estado, con actor, detalle y marca de tiempo.

Transiciones permitidas para el recolector: `programada` → `en_camino` → `recolectando` → `recolectada`. El cierre exige evidencia fotográfica, peso positivo y tipo de material.
