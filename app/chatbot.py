"""Asistente local de EcoConecta. No usa APIs pagas ni envía datos a terceros."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

STOPWORDS = {
    "a", "al", "algo", "algun", "alguna", "algunas", "algunos", "como", "con", "cual",
    "cuando", "cuanto", "cuantos", "de", "del", "desde", "donde", "el", "ella", "ellas",
    "ello", "ellos", "en", "entre", "es", "esa", "ese", "eso", "esta", "este", "esto",
    "hay", "la", "las", "lo", "los", "mas", "me", "mi", "mis", "muy", "no", "o", "para",
    "pero", "por", "que", "se", "si", "sin", "sobre", "su", "sus", "te", "tengo", "tiene",
    "tu", "tus", "un", "una", "unas", "uno", "unos", "y", "ya", "quiero", "puedo", "pueden",
}

SYNONYMS = {
    "basura": "residuo residuos", "desecho": "residuo residuos", "desechos": "residuo residuos",
    "organica": "organico compostaje", "organicas": "organico compostaje", "comida": "organico restos alimentos",
    "sobras": "organico restos alimentos", "reciclaje": "reciclable reciclar aprovechamiento",
    "reciclar": "reciclable reciclaje aprovechamiento", "plastico": "plasticos envases",
    "botella": "plasticos envases", "botellas": "plasticos envases", "carton": "papel carton",
    "papeles": "papel carton", "latas": "metales aluminio", "lata": "metales aluminio",
    "recoleccion": "solicitud recoger ruta recoger", "recoger": "solicitud recoleccion ruta",
    "camion": "recoleccion recolector ruta", "carro": "recoleccion recolector ruta",
    "puntos": "puntos incentivo puntaje", "puntaje": "puntos incentivo",
    "clave": "contrasena acceso cuenta", "password": "contrasena acceso cuenta",
    "entrar": "iniciar sesion acceso cuenta", "ingresar": "iniciar sesion acceso cuenta",
    "usuario": "cuenta ciudadano perfil", "perfil": "cuenta ciudadano perfil",
    "demora": "horario fecha programacion retraso", "tarde": "retraso horario programacion",
    "aceite": "aceite usado especial", "pila": "baterias pilas especial", "pilas": "baterias pilas especial",
    "electronico": "residuos aparatos electricos especiales", "computador": "residuos aparatos electricos especiales",
    "celular": "residuos aparatos electricos especiales", "vidrio": "vidrio envases",
}

@dataclass(frozen=True)
class Knowledge:
    category: str
    terms: tuple[str, ...]
    answer: str

KB = [
    Knowledge("bienvenida", ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "saludos"),
              "¡Hola! Soy EcoBot, el asistente de EcoConecta. Puedo orientarte sobre separación de residuos, solicitudes de recolección, seguimiento, puntos y uso de la plataforma. ¿Qué necesitas saber?"),
    Knowledge("que_es", ("que es ecoconecta", "para que sirve ecoconecta", "como funciona el programa", "proyecto ecoconecta", "objetivo"),
              "EcoConecta es una plataforma comunitaria para facilitar la separación y el aprovechamiento de residuos. Permite a los ciudadanos registrar solicitudes, consultar su seguimiento y conocer los puntos que se acreditan después de una recolección verificada. También facilita la coordinación entre ciudadanos, coordinadores y recolectores."),
    Knowledge("crear_cuenta", ("crear cuenta", "registrarme", "registro", "abrir cuenta", "inscribirme"),
              "Para crear una cuenta, entra al botón «Mi cuenta», selecciona «Crear cuenta» y completa nombre, teléfono, dirección, correo opcional y una contraseña de al menos 8 caracteres. El registro público crea una cuenta de ciudadano; los roles de coordinador, recolector y administrador los asigna personal autorizado."),
    Knowledge("iniciar_sesion", ("iniciar sesion", "entrar a mi cuenta", "no puedo ingresar", "olvido contrasena", "recuperar contrasena", "problema acceso"),
              "Para ingresar, abre «Mi cuenta» y utiliza el teléfono y la contraseña con los que te registraste. Si olvidaste la contraseña o no puedes entrar, solicita ayuda al equipo administrador. No compartas tu contraseña ni códigos de acceso por el chat."),
    Knowledge("solicitud", ("hacer solicitud", "crear solicitud", "solicitar recoleccion", "solicito una recoleccion", "como solicito una recoleccion", "pedir recoleccion", "pedir que recojan", "agendar recoleccion", "necesito recoger residuos"),
              "Para solicitar una recolección, inicia sesión como ciudadano, abre «Solicitar recolección», selecciona el flujo orgánico o reciclable, indica el tipo de generador, dirección, horario preferido y observaciones. Al enviar, recibirás un código de seguimiento. La solicitud queda pendiente de gestión del colectivo correspondiente."),
    Knowledge("tipos", ("que residuos reciben", "que residuos recibe ecoconecta", "que materiales reciben", "tipos de residuos", "que puedo entregar", "que se puede reciclar", "materiales aceptados"),
              "EcoConecta contempla dos flujos de solicitud: orgánicos y reciclables. Entre los reciclables comunes están papel y cartón limpios y secos, envases plásticos aprovechables, vidrio y metales. Los residuos orgánicos incluyen restos vegetales y de alimentos aptos para aprovechamiento. Si tienes un material especial o dudoso, descríbelo en las observaciones antes de entregarlo."),
    Knowledge("organicos", ("residuos organicos", "restos de comida", "cascara de frutas", "cascaras", "compost", "compostaje", "residuos de cocina"),
              "Los residuos orgánicos pueden incluir cáscaras de frutas y verduras, restos vegetales y otros residuos biodegradables de cocina. Sepáralos de plásticos, vidrio, metales y productos químicos. Evita incluir aceites, pilas, medicamentos o residuos peligrosos. Para solicitar su recolección, elige el flujo «Orgánico»."),
    Knowledge("reciclables", ("residuos reciclables", "separar reciclaje", "aprovechables", "material aprovechable"),
              "Separa los materiales aprovechables y entrégalos limpios y secos. Mantén papel y cartón lejos de líquidos y restos de comida; enjuaga y seca los envases cuando sea posible; aplana las cajas para facilitar el almacenamiento. En EcoConecta selecciona el flujo «Reciclable»."),
    Knowledge("papel_carton", ("papel", "carton", "cuadernos", "periodico", "cajas"),
              "El papel y el cartón deben estar limpios y secos. Evita entregarlos mojados, grasosos o contaminados con comida. Pliega las cajas y almacénalos separados de los residuos orgánicos."),
    Knowledge("plasticos", ("plastico", "plasticos", "botellas plasticas", "envases", "bolsas plasticas"),
              "Los envases plásticos aprovechables deben estar vacíos, limpios y secos. Cuando sea posible, aplástalos para reducir su volumen. No mezcles envases con residuos químicos o sustancias peligrosas; si no sabes si un plástico se recibe, descríbelo en las observaciones de tu solicitud."),
    Knowledge("vidrio", ("vidrio", "botellas de vidrio", "frascos", "envases de vidrio"),
              "Los envases de vidrio deben entregarse vacíos y separados. Manipula con cuidado cualquier vidrio roto y no lo entregues suelto: envuélvelo y advierte al equipo en las observaciones. Confirma con el colectivo si recibe vidrio roto antes de incluirlo."),
    Knowledge("metales", ("metal", "metales", "aluminio", "latas", "chatarra"),
              "Las latas y otros metales aprovechables deben estar vacíos y, de ser posible, limpios. Separa objetos cortantes o voluminosos y consulta con el colectivo antes de entregarlos."),
    Knowledge("aceite", ("aceite usado", "aceite de cocina", "aceite quemado"),
              "No viertas aceite usado por el desagüe ni lo mezcles con residuos orgánicos o reciclables comunes. Guárdalo frío en un recipiente cerrado y consulta con un gestor autorizado o con el equipo de EcoConecta si existe una ruta específica. No puedo confirmar que el programa tenga actualmente una ruta de aceite."),
    Knowledge("pilas", ("pilas", "baterias", "bateria", "baterias usadas"),
              "Las pilas y baterías requieren manejo posconsumo especial. No las mezcles con residuos domésticos ni las abras, quemes o perfores. Llévalas a un punto de recolección autorizado para ese tipo de residuo. EcoConecta no debe registrar estos materiales como orgánicos o reciclables comunes sin confirmación del equipo."),
    Knowledge("electronicos", ("residuos electronicos", "aparatos electronicos", "computador", "celular", "cargador", "electrodomestico"),
              "Los aparatos eléctricos y electrónicos requieren canales posconsumo o gestores autorizados. No los desarmes ni los mezcles con la recolección ordinaria. Consulta un punto autorizado y pregunta al equipo de EcoConecta si existe una campaña específica."),
    Knowledge("separacion", ("como separar residuos", "separacion en la fuente", "clasificar basura", "separar en casa"),
              "En casa puedes comenzar con dos grupos de EcoConecta: orgánicos y reciclables. Mantén los orgánicos separados; conserva papel, cartón y envases aprovechables limpios y secos; y aparta pilas, medicamentos, químicos y electrónicos para canales especiales. Si un material genera dudas, no lo mezcles: consulta antes de entregarlo."),
    Knowledge("contaminacion", ("residuos contaminados", "material sucio", "papel mojado", "envases sucios", "mezclados"),
              "Los materiales contaminados con comida, grasa, químicos o líquidos pueden perder su aprovechamiento y afectar otros residuos. Mantén separados los materiales, limpia y seca los envases cuando sea seguro hacerlo y no mezcles sustancias peligrosas."),
    Knowledge("seguimiento", ("consultar solicitud", "estado de solicitud", "seguimiento", "codigo solicitud", "donde va mi recoleccion", "ver mi pedido"),
              "Para consultar una solicitud, inicia sesión con tu cuenta ciudadana y entra en «Mis solicitudes». Allí puedes revisar el código, el estado y el historial disponible. El seguimiento puede mostrar estados como recibida, asignada, programada, en camino, recolectando y recolectada. El chatbot público no puede consultar datos privados por ti."),
    Knowledge("estados", ("recibida", "asignada", "programada", "en camino", "recolectando", "recolectada", "estado recoleccion"),
              "Los estados indican el avance de la solicitud: «Recibida» significa que fue registrada; «Asignada», que tiene un responsable; «Programada», que cuenta con fecha y hora; «En camino», que el recolector inició el recorrido; «Recolectando», que la actividad está en curso; y «Recolectada», que se cerró con el registro correspondiente."),
    Knowledge("horarios", ("horario", "cuando pasan", "que dias recogen", "dias de recoleccion", "hora de recoleccion", "ruta hoy"),
              "Los horarios y fechas se confirman cuando el coordinador programa la solicitud. No tengo un calendario general confirmado ni debo inventar días de ruta. Revisa «Mis solicitudes» después de iniciar sesión para consultar la fecha y hora asignadas."),
    Knowledge("retraso", ("no llegaron", "no recogieron", "no pasaron", "retraso", "incumplimiento", "no vinieron", "no vienen a recoger", "no vino el recolector", "no paso el camion", "no cumplieron la ruta"),
              "Si el equipo no llegó en la fecha programada, consulta primero el estado y los datos de la solicitud en «Mis solicitudes». Después contacta al equipo de coordinación e indica el código de solicitud, la dirección y la fecha programada. No crees una solicitud duplicada mientras se revisa la anterior."),
    Knowledge("puntos", ("puntos", "ganar puntos", "acumular puntos", "como se calculan puntos", "recompensas", "incentivos"),
              "Los puntos se acreditan cuando el recolector finaliza la solicitud y registra el peso y la evidencia. La regla de cálculo depende del parámetro configurado por la plataforma. En esta versión, la equivalencia visible es demostrativa y debe validarse con la entidad responsable; no representa por sí sola un catálogo oficial de premios."),
    Knowledge("evidencia", ("foto", "fotografia", "evidencia", "peso", "kilogramos", "registrar recoleccion"),
              "Al finalizar una recolección, el recolector autorizado registra el peso, el tipo de material y una fotografía de evidencia. El sistema guarda ese registro en el historial y calcula los puntos según la regla configurada. La evidencia solo debe corresponder a la recolección real."),
    Knowledge("roles", ("administrador", "coordinador", "recolector", "roles", "permisos", "quien puede ver"),
              "EcoConecta diferencia los perfiles. El ciudadano crea y consulta sus propias solicitudes. La coordinación gestiona las solicitudes de su flujo y asigna recolectores. El recolector consulta únicamente las tareas asignadas y registra avances y evidencias. El administrador tiene una vista global. Los permisos se validan en el servidor, no solo ocultando botones."),
    Knowledge("admin", ("panel administrador", "administracion", "administrador general", "gestionar usuarios", "panel admin"),
              "El administrador inicia sesión desde «Mi cuenta». Si la cuenta tiene el rol admin, el sistema muestra el panel administrativo global con solicitudes, indicadores y seguimiento de todos los flujos. El registro público no permite elegir ni solicitar el rol de administrador."),
    Knowledge("notificaciones", ("notificaciones", "avisos", "alertas", "mensaje al coordinador", "aviso recolector"),
              "EcoConecta genera notificaciones internas para los usuarios responsables según el flujo y el estado de la solicitud. La entrega de mensajes automáticos por WhatsApp requiere una cuenta y configuración oficial de WhatsApp Business Platform; en el modo gratuito actual no se envían mensajes externos automáticamente."),
    Knowledge("whatsapp", ("whatsapp", "whatsapp business", "mensaje whatsapp", "recibir por whatsapp"),
              "La plataforma conserva las notificaciones internas. Para enviar mensajes automáticos por WhatsApp se necesita configurar una cuenta de Meta, WhatsApp Business Platform, un número autorizado, consentimiento de los destinatarios y revisar las tarifas y límites vigentes. Como EcoConecta está trabajando con presupuesto cero, esa conexión queda desactivada hasta que se autorice expresamente."),
    Knowledge("privacidad", ("datos personales", "privacidad", "seguridad", "contrasena", "mis datos", "datos de otros"),
              "No compartas contraseñas ni códigos de acceso. EcoConecta debe mostrar a cada ciudadano únicamente sus propios registros; los coordinadores solo deben gestionar su flujo; y los recolectores, sus asignaciones. Para consultar datos de cuenta, inicia sesión. No publiques el archivo .env ni claves API en GitHub."),
    Knowledge("contacto", ("contactar", "contacto", "hablar con alguien", "ayuda humana", "soporte", "equipo ecoconecta"),
              "Si necesitas atención humana, utiliza los canales oficiales que la organización haya publicado o solicita al administrador que te indique el contacto vigente. No tengo un número de atención confirmado y no voy a inventarlo."),
    Knowledge("cobertura", ("cobertura", "barrios", "donde funciona", "villas de san pablo", "barranquilla", "ubicacion"),
              "La información del proyecto identifica a Villas de San Pablo, Barranquilla, como comunidad de referencia. No tengo confirmada una cobertura adicional ni puedo prometer recolecciones fuera de las zonas habilitadas. Consulta al equipo antes de crear una solicitud desde otro sector."),
    Knowledge("problema", ("error", "no funciona", "pagina no abre", "problema tecnico", "fallo", "no carga"),
              "Para ayudarte con un problema técnico, dime qué estabas intentando hacer, qué mensaje de error apareció y en qué sección ocurrió. No compartas contraseñas, tokens ni claves. Si se trata de una solicitud, incluye solo su código, nunca datos sensibles de otras personas."),
    Knowledge("despedida", ("gracias", "muchas gracias", "listo gracias", "hasta luego", "adios"),
              "¡Con gusto! Gracias por participar en EcoConecta. Separar correctamente los residuos ayuda a aprovechar materiales y cuidar nuestra comunidad. ♻️"),
]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> set[str]:
    words = set(normalize(text).split()) - STOPWORDS
    expanded = set(words)
    for word in words:
        expanded.update(SYNONYMS.get(word, "").split())
    return expanded


def answer_question(question: str, history: list[dict] | None = None) -> dict:
    clean = normalize(question)
    if not clean:
        return {"answer": "Escribe tu pregunta y con gusto te orientaré sobre EcoConecta.", "category": "general", "confidence": 0.0}

    # Intenciones explícitas: evita que palabras como "cuando" o "solicitud"
    # desvíen una consulta de seguimiento hacia la categoría de horarios.
    delay_patterns = (
        r"\b(que pasa|que hago|que puedo hacer|que hago si)\b.*\b(no vienen|no vinieron|no llegaron|no recogieron|no pasaron|no paso|no vino|no cumplen|no cumplieron)\b",
        r"\b(retraso|demora|incumplimiento)\b.*\b(recoleccion|recolector|ruta|solicitud|residuos)\b",
        r"\b(recolector|equipo|camion)\b.*\b(no vino|no llego|no paso|no recogio)\b",
        r"\b(no vienen a recoger|no han recogido|no han pasado|se retraso la recoleccion)\b",
    )
    if any(re.search(pattern, clean) for pattern in delay_patterns):
        item = next(entry for entry in KB if entry.category == "retraso")
        return {"answer": item.answer, "category": item.category, "confidence": 0.98}

    tracking_patterns = (
        r"\b(consult(ar|o|a|ar mi)|ver|revis(ar|o)|mir(ar|o)|estado|seguimiento)\b.*\b(solicitud|recoleccion|pedido|codigo|estado)\b",
        r"\b(donde|como)\b.*\b(veo|consulto|reviso|miro|consultar|ver)\b.*\b(solicitud|recoleccion|pedido)\b",
        r"\b(ya recogieron|recogieron|recolectaron)\b.*\b(residuos|solicitud|pedido|material)\b",
        r"\b(que paso|como va|en que estado)\b.*\b(solicitud|recoleccion|pedido)\b",
        r"\b(codigo)\b.*\b(seguimiento|solicitud|pedido)\b",
    )
    if any(re.search(pattern, clean) for pattern in tracking_patterns):
        item = next(entry for entry in KB if entry.category == "seguimiento")
        return {"answer": item.answer, "category": item.category, "confidence": 0.98}

    # Intenciones de horario solo cuando la pregunta realmente pide fecha u hora,
    # y no cuando consulta el estado de una solicitud.
    if re.search(r"\b(cuando|que dia|a que hora|horario|fecha|ruta)\b", clean) and not re.search(r"\b(estado|seguimiento|consultar|consulto|revisar|reviso|ver|veo)\b", clean):
        item = next(entry for entry in KB if entry.category == "horarios")
        if re.search(r"\b(pasa|pasan|recogen|recoleccion|ruta|horario|hora)\b", clean):
            return {"answer": item.answer, "category": item.category, "confidence": 0.86}

    # Las preguntas de seguimiento heredan términos de la última intervención del usuario.
    previous_user = ""
    if history:
        for item in reversed(history[:-1]):
            if item.get("role") == "user":
                previous_user = str(item.get("content", ""))
                break
    query_tokens = tokens(clean)
    if len(query_tokens) <= 3 and previous_user:
        previous_result = answer_question(previous_user, None)
        if previous_result["category"] != "sin_coincidencia":
            return {
                "answer": "Sobre lo que preguntaste antes: " + previous_result["answer"],
                "category": previous_result["category"],
                "confidence": previous_result["confidence"],
            }
        query_tokens |= tokens(previous_user)

    best_item = None
    best_score = 0.0
    for item in KB:
        term_tokens = set()
        normalized_terms = [normalize(term) for term in item.terms]
        for term in normalized_terms:
            term_tokens |= tokens(term)
            if term and term in clean:
                best_score = max(best_score, 0.92)
                best_item = item
        if not query_tokens or not term_tokens:
            continue
        overlap = len(query_tokens & term_tokens)
        precision = overlap / max(1, len(query_tokens))
        recall = overlap / max(1, len(term_tokens))
        score = (2 * precision * recall / (precision + recall)) if precision + recall else 0
        # Prioriza preguntas que comparten términos poco comunes y varias palabras.
        score += min(overlap, 4) * 0.035
        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score >= 0.18:
        return {"answer": best_item.answer, "category": best_item.category, "confidence": round(min(best_score, 1.0), 2)}

    return {
        "answer": (
            "No tengo información confirmada para responder eso con seguridad. Puedo orientarte sobre la plataforma, "
            "solicitudes y seguimiento, separación de residuos, orgánicos, reciclables, puntos, perfiles y notificaciones. "
            "¿Puedes reformular la pregunta o contarme qué material o trámite necesitas consultar? Si se trata de un horario, "
            "una ruta o un dato de tu cuenta, debes confirmarlo en el panel o con el equipo responsable."
        ),
        "category": "sin_coincidencia",
        "confidence": round(best_score, 2),
    }
