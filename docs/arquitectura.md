# Arquitectura de EcoConecta

## Vista lógica

```mermaid
flowchart LR
  subgraph Clientes
    H[Hogares y negocios]
    CO[Coordinadores]
    RE[Recolectores]
  end
  UI[Web responsive<br/>HTML + CSS + JavaScript]
  API[FastAPI]
  SEC[Autenticación JWT<br/>Autorización por rol]
  SRV[Servicios de solicitudes<br/>asignación y programación]
  PTS[Servicio de puntos]
  PG[(PostgreSQL)]
  H --> UI
  CO --> UI
  RE --> UI
  UI <-->|HTTPS / JSON| API
  API --> SEC
  API --> SRV
  SRV --> PTS
  SEC --> PG
  SRV --> PG
  PTS --> PG
```

## Componentes

- **Interfaz:** aplicación web adaptable a móvil y escritorio. Presenta vistas de comunidad y operación.
- **API:** FastAPI expone endpoints REST, valida entradas con Pydantic y aplica reglas de negocio.
- **Identidad:** contraseñas cifradas y tokens JWT; cada endpoint restringe las acciones por rol.
- **Persistencia:** PostgreSQL almacena usuarios, solicitudes e historial.
- **Puntos:** cálculo determinista y parametrizable ejecutado únicamente al registrar el cierre de la recolección.
- **Contenedor:** Docker empaqueta la aplicación; Docker Compose orquesta API y PostgreSQL en desarrollo.

## Separación de flujos

| Flujo | Colectivo responsable | Perfil coordinador | Perfil recolector |
|---|---|---|---|
| Orgánico | Huerteros | `coordinator_garden` | `collector_garden` |
| Reciclable | Recicladores | `coordinator_recycling` | `collector_recycling` |

## Secuencia de atención

```mermaid
sequenceDiagram
  actor Persona as Usuario
  participant Web as Plataforma
  participant API as FastAPI
  participant DB as PostgreSQL
  actor Coord as Coordinador
  actor Reco as Recolector
  Persona->>Web: Registra residuo y ubicación
  Web->>API: POST /api/requests
  API->>API: Clasifica el flujo
  API->>DB: Guarda solicitud e historial
  API-->>Persona: Código y confirmación
  Coord->>API: Revisa y programa
  API->>DB: Guarda fecha, hora y responsable
  Reco->>API: Registra peso y recolección
  API->>DB: Cierra solicitud y acredita puntos
  API-->>Persona: Saldo actualizado
```

## Seguridad y privacidad

- Los endpoints requieren token, salvo registro, login y health check.
- Las funciones de coordinación se restringen al flujo de su colectivo.
- El recolector solo puede cerrar solicitudes asignadas a su usuario.
- El usuario de comunidad solo consulta sus propias solicitudes e historial.
- El acceso a contacto y dirección se limita a perfiles operativos.
- Secretos se suministran mediante variables de entorno, nunca desde el repositorio.
