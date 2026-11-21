# Guion de sustentación · EcoConecta

## 1. Problema
En Villas de San Pablo existen iniciativas comunitarias para aprovechar residuos orgánicos y reciclables. El diagnóstico identifica comunicación fragmentada, desconocimiento de rutas y actores, educación ambiental insuficiente y dificultades para coordinar la recolección.

## 2. Usuarios
Hogares, unidades productivas, coordinadores de huerteros, huerteros, coordinadores de recicladores, recicladores y administración.

## 3. Solución
EcoConecta organiza en un solo canal la educación ambiental y la solicitud de recolección. La clasificación del residuo dirige la solicitud al colectivo adecuado. El coordinador revisa y programa; el responsable registra la recolección; el sistema conserva evidencia y reconoce la participación mediante puntos configurables.

## 4. Decisiones técnicas
- HTML, CSS y JavaScript para una interfaz directa y adaptable.
- Python y FastAPI para API REST y reglas de negocio.
- PostgreSQL como base de datos relacional.
- SQLAlchemy, Psycopg y Pydantic para persistencia y validación.
- Docker y Git para reproducibilidad y control de versiones.

## 5. Impacto esperado
Mejorar la claridad de las rutas, reducir pérdida de solicitudes, facilitar la coordinación entre comunidad y colectivos, y fortalecer la educación ambiental. El impacto deberá medirse con datos del piloto: solicitudes recibidas, tiempos de programación, recolecciones completadas, kilogramos aprovechados y participación recurrente.

## 6. Limitaciones transparentes
La integración real de WhatsApp requiere credenciales, plantillas y webhook oficiales. La IA no se incorporó al núcleo del MVP para priorizar el recorrido operativo y mantener las decisiones críticas bajo control humano. La equivalencia de puntos es demostrativa y requiere validación institucional. Las cuentas y datos actuales son ficticios.

## 7. Demostración
Ejecutar un caso orgánico de extremo a extremo y repetirlo con reciclables para evidenciar el enrutamiento independiente. Mostrar que la programación exige fecha, hora y recolector y que los puntos solo se acreditan después del cierre.
