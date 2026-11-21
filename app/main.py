from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from collections import defaultdict, deque
from threading import Lock
import logging
import httpx
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request as HttpRequest
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, inspect
from .database import Base, engine, get_db
from .models import User, Request, RequestEvent, CollectionEvidence, Notification
from .schemas import RegisterInput, LoginInput, RequestInput, AssignInput, ScheduleInput, CloseInput, AdvanceInput, ChatInput, AdminUserUpdate
from .security import hash_password, verify_password, create_token, current_user, require_roles
from .config import settings
from .chatbot import answer_question

# Limitador local por proceso. En despliegues multi-worker debe sustituirse
# por un backend compartido (Redis/API gateway).
_logger = logging.getLogger("ecoconecta.integrations")
_chat_attempts = defaultdict(deque)
_chat_lock = Lock()
_chat_window_seconds = 60
_chat_max_attempts = 12

_login_attempts = defaultdict(deque)
_login_lock = Lock()
_LOGIN_WINDOW_SECONDS = 900
_LOGIN_MAX_ATTEMPTS = 8
_LOGIN_BLOCK_SECONDS = 900


def check_login_rate_limit(key: str):
    now = datetime.utcnow().timestamp()
    with _login_lock:
        attempts = _login_attempts[key]
        while attempts and now - attempts[0] > _LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
            raise HTTPException(429, "Demasiados intentos. Intenta nuevamente en 15 minutos.")


def record_login_failure(key: str):
    with _login_lock:
        _login_attempts[key].append(datetime.utcnow().timestamp())


def clear_login_failures(key: str):
    with _login_lock:
        _login_attempts.pop(key, None)



def migrate_legacy_users_table():
    """Completa columnas faltantes sin borrar datos."""
    inspector = inspect(engine)

    if "users" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    with engine.begin() as connection:

        if "full_name" not in columns:
            if "name" in columns:
                connection.execute(text(
                    'ALTER TABLE users RENAME COLUMN "name" TO full_name'
                ))
                
            else:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN full_name VARCHAR(120)"
                ))
            columns.add("full_name")

        missing_columns = {
            "address": "VARCHAR(240)",
            "email": "VARCHAR(160)",
            "password_hash": "VARCHAR(255)",
            "role": "VARCHAR(40) NOT NULL DEFAULT 'community'",
            "active": "BOOLEAN NOT NULL DEFAULT TRUE",
            "points": "INTEGER NOT NULL DEFAULT 0",
            "created_at": (
                "TIMESTAMP WITHOUT TIME ZONE "
                "NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ),
        }

        for name, column_type in missing_columns.items():
            if name not in columns:
                connection.execute(text(
                    f'ALTER TABLE users ADD COLUMN "{name}" {column_type}'
                ))
                columns.add(name)
                _logger.warning(
                    "Columna agregada a users: %s", name
                )
                connection.execute(text(
            "ALTER TABLE users ALTER COLUMN email DROP NOT NULL"
        ))

        connection.execute(text("""
            UPDATE users
            SET full_name = COALESCE(
                NULLIF(BTRIM(full_name), ''),
                NULLIF(BTRIM(phone), ''),
                'Usuario ' || id::text
            )
            WHERE full_name IS NULL OR BTRIM(full_name) = ''
        """))

        connection.execute(text(
            "ALTER TABLE users ALTER COLUMN full_name SET NOT NULL"
        ))
                # Sincronizar el consecutivo de usuarios existentes
        sequence_name = connection.scalar(text(
            "SELECT pg_get_serial_sequence('users', 'id')"
        ))

        if not sequence_name:
            connection.execute(text(
                "CREATE SEQUENCE IF NOT EXISTS users_id_seq"
            ))
            connection.execute(text(
                "ALTER TABLE users ALTER COLUMN id "
                "SET DEFAULT nextval('users_id_seq')"
            ))
            connection.execute(text(
                "ALTER SEQUENCE users_id_seq OWNED BY users.id"
            ))
            sequence_name = "users_id_seq"

        connection.execute(
            text("""
                SELECT setval(
                    CAST(:sequence_name AS regclass),
                    GREATEST(COALESCE((SELECT MAX(id) FROM users), 0), 1),
                    EXISTS (SELECT 1 FROM users)
                )
            """),
            {"sequence_name": sequence_name}
        )

    _logger.info(
        "Migración de la tabla users completada correctamente."
    )



@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_legacy_users_table()
    yield



def normalize_colombian_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    if digits.startswith("00"):
        return digits[2:]
    return digits


def send_whatsapp_text(phone: str, message: str) -> bool:
    """Envía texto por Cloud API. Requiere opt-in y ventana de atención de 24 h.
    Para mensajes proactivos fuera de esa ventana debe configurarse una plantilla aprobada.
    """
    cfg = settings
    if not (cfg.whatsapp_enabled and cfg.whatsapp_token and cfg.whatsapp_phone_number_id and cfg.whatsapp_api_version):
        return False
    recipient = normalize_colombian_phone(phone)
    if len(recipient) < 10:
        _logger.warning("WhatsApp omitido: teléfono inválido")
        return False
    url = f"https://graph.facebook.com/{cfg.whatsapp_api_version}/{cfg.whatsapp_phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {cfg.whatsapp_token}", "Content-Type": "application/json"}
    if cfg.whatsapp_template_name:
        # Plantilla de utilidad aprobada en Meta con un parámetro {{1}} en el cuerpo.
        payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient,
                   "type": "template", "template": {"name": cfg.whatsapp_template_name,
                   "language": {"code": cfg.whatsapp_template_language},
                   "components": [{"type": "body", "parameters": [{"type": "text", "text": message[:900]}]}]}}
    else:
        payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient,
                   "type": "text", "text": {"preview_url": False, "body": message[:4000]}}
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=12.0)
        response.raise_for_status()
        return True
    except Exception as exc:
        _logger.warning("No se pudo enviar notificación WhatsApp: %s", type(exc).__name__)
        return False


def notify_whatsapp_users(users, title: str, message: str):
    body = f"EcoConecta | {title}\n{message}"
    # Protección por consentimiento: solo se envía a números incluidos explícitamente
    # en WHATSAPP_ALLOWED_RECIPIENTS. Sin lista, no sale ningún mensaje externo.
    allowed = {
        normalize_colombian_phone(value.strip())
        for value in settings.whatsapp_allowed_recipients.split(",")
        if value.strip()
    }
    if not allowed:
        return
    for recipient in users:
        if recipient and recipient.phone and normalize_colombian_phone(recipient.phone) in allowed:
            send_whatsapp_text(recipient.phone, body)


def check_chat_rate_limit(key: str):
    now = datetime.utcnow().timestamp()
    with _chat_lock:
        attempts = _chat_attempts[key]
        while attempts and now - attempts[0] > _chat_window_seconds:
            attempts.popleft()
        if len(attempts) >= _chat_max_attempts:
            raise HTTPException(429, "Has enviado muchas preguntas. Espera un minuto e inténtalo nuevamente.")
        attempts.append(now)


app = FastAPI(title="EcoConecta API", version="2.0.1", lifespan=lifespan)

@app.middleware("http")
async def security_headers(request: HttpRequest, call_next):
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("application/json"):
        response.headers["content-type"] = "application/json; charset=utf-8"
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response

app.mount("/static", StaticFiles(directory="app/static"), name="static")
Path("uploads").mkdir(exist_ok=True)

@app.get("/")
def home(): return FileResponse("app/static/index.html")

@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "La base de datos no está disponible")
    return {"status":"ok", "database":"PostgreSQL", "application":"EcoConecta"}

@app.post("/api/auth/register")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    phone = data.phone.strip()
    email = data.email.strip().lower() if data.email else None

    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(409, "Este teléfono ya está registrado")

    if email and db.scalar(
        select(User).where(func.lower(User.email) == email)
    ):
        raise HTTPException(409, "Este correo electrónico ya está registrado")

    user = User(
        full_name=data.full_name.strip(),
        phone=phone,
        email=email,
        address=data.address.strip() if data.address else None,
        password_hash=hash_password(data.password),
        role="community"
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()

        _logger.exception(
            "ERROR REAL AL REGISTRAR USUARIO. Teléfono terminado en %s",
            phone[-4:]
        )

        raise HTTPException(
            500,
            "No fue posible guardar la cuenta. "
            "Consulta los registros del servidor."
        ) from None

    return {
        "access_token": create_token(user),
        "token_type": "bearer",
        "user": user_data(user)
    }



def user_data(user):
    return {"id":user.id,"name":user.full_name,"phone":user.phone,"role":user.role,"points":user.points}


def ensure_request_access(req: Request, user: User):
    """Apply request-level authorization before exposing history or changing state."""
    if user.role == "admin":
        return
    if user.role == "community" and req.user_id == user.id:
        return
    if user.role == "coordinator_garden" and req.flow == "organico":
        return
    if user.role == "coordinator_recycling" and req.flow == "reciclable":
        return
    if user.role in ("collector_garden", "collector_recycling") and req.collector_id == user.id:
        return
    raise HTTPException(403, "No tienes permisos para consultar o modificar esta solicitud")

def add_notification(db: Session, user_id: int | None, title: str, message: str, request_id: int | None = None):
    if user_id is not None:
        db.add(Notification(user_id=user_id, request_id=request_id, title=title, message=message))

def staff_for_flow(db: Session, flow: str):
    role = "coordinator_garden" if flow == "organico" else "coordinator_recycling"
    return db.scalars(select(User).where(User.role == role, User.active.is_(True))).all()


def admins_for_notifications(db: Session):
    """Administradores activos reciben alertas globales sin ampliar sus permisos de escritura."""
    return db.scalars(select(User).where(User.role == "admin", User.active.is_(True))).all()


def notify_admins(db: Session, title: str, message: str, request_id: int | None = None):
    for administrator in admins_for_notifications(db):
        add_notification(db, administrator.id, title, message, request_id)

@app.post("/api/auth/login")
def login(data: LoginInput, request: HttpRequest, db: Session = Depends(get_db)):
    phone = data.phone.strip()
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{phone}"
    check_login_rate_limit(rate_key)
    user = db.scalar(select(User).where(User.phone == phone))
    if not user or not verify_password(data.password, user.password_hash):
        record_login_failure(rate_key)
        raise HTTPException(401, "Teléfono o contraseña incorrectos")
    if not user.active:
        raise HTTPException(403, "Esta cuenta se encuentra deshabilitada")
    clear_login_failures(rate_key)
    return {"access_token":create_token(user), "token_type":"bearer", "user":user_data(user)}

@app.get("/api/me")
def me(user: User = Depends(current_user)): return user_data(user)

@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    rows = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [{"id": u.id, "name": u.full_name, "phone": u.phone, "email": u.email,
             "role": u.role, "active": u.active, "points": u.points,
             "created_at": u.created_at.isoformat()} for u in rows]

@app.patch("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, data: AdminUserUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Usuario no encontrado")
    if target.id == user.id and (data.active is False or (data.role and data.role != "admin")):
        raise HTTPException(409, "No puedes desactivar ni quitarte el rol de administrador durante tu propia sesión")
    removing_active_admin = target.role == "admin" and target.active and (
        data.active is False or (data.role is not None and data.role != "admin")
    )
    if removing_active_admin:
        active_admins = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.active.is_(True))) or 0
        if active_admins <= 1:
            raise HTTPException(409, "Debe permanecer al menos un administrador activo")
    if data.role is not None:
        target.role = data.role
    if data.active is not None:
        target.active = data.active
    db.commit()
    db.refresh(target)
    return {"id": target.id, "name": target.full_name, "role": target.role, "active": target.active}

@app.post("/api/requests", status_code=201)
def create_request(data: RequestInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != "community":
        raise HTTPException(403, "Solo las cuentas ciudadanas pueden crear solicitudes")
    if data.waste_type not in ("organico", "reciclable"):
        raise HTTPException(422, "Selecciona orgánico o reciclable")
    flow = "organico" if data.waste_type == "organico" else "reciclable"
    code = "EC-" + datetime.now().strftime("%y%m%d") + "-" + uuid4().hex[:5].upper()
    req = Request(code=code, user_id=user.id, generator_type=data.generator_type, waste_type=data.waste_type,
                  flow=flow, address=data.address, notes=data.notes, preferred_time=data.preferred_time)
    db.add(req); db.flush()
    db.add(RequestEvent(request_id=req.id, actor_id=user.id, status="recibida", detail=f"Enrutada al colectivo de {'huerteros' if flow == 'organico' else 'recicladores'}"))
    coordinators = staff_for_flow(db, flow)
    for coordinator in coordinators:
        add_notification(db, coordinator.id, "Nueva solicitud recibida", f"{code}: nueva solicitud de {user.full_name} para el flujo {flow}.", req.id)
    notify_admins(db, "Nueva solicitud recibida", f"{code}: nueva solicitud de {user.full_name} para el flujo {flow}.", req.id)
    db.commit(); db.refresh(req)
    coordinators = staff_for_flow(db, flow)
    notify_whatsapp_users(coordinators + admins_for_notifications(db), "Nueva solicitud recibida",
        f"Código: {code}\nTipo: {flow}\nGenerador: {data.generator_type}\nDirección: {data.address}\nCiudadano: {user.full_name}")
    return request_data(req, include_private=True)

def request_data(req, include_private=False):
    out = {"id":req.id,"code":req.code,"flow":req.flow,"waste_type":req.waste_type,"status":req.status,
           "created_at":req.created_at.isoformat(),"scheduled_date":req.scheduled_date.isoformat() if req.scheduled_date else None,
           "scheduled_time":req.scheduled_time.strftime("%H:%M") if req.scheduled_time else None,
           "points_awarded":req.points_awarded,"weight_kg":req.weight_kg,"collector_name":(req.collector.full_name if getattr(req, "collector", None) else None)}
    if include_private: out.update({"address":req.address,"notes":req.notes,"preferred_time":req.preferred_time,"user_name":req.user.full_name,"phone":req.user.phone})
    return out

@app.get("/api/requests")
def list_requests(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = select(Request).order_by(Request.created_at.desc())
    if user.role == "community": query = query.where(Request.user_id == user.id)
    elif user.role == "coordinator_garden": query = query.where(Request.flow == "organico")
    elif user.role == "coordinator_recycling": query = query.where(Request.flow == "reciclable")
    elif user.role == "collector_garden": query = query.where(Request.collector_id == user.id)
    elif user.role == "collector_recycling": query = query.where(Request.collector_id == user.id)
    rows = db.scalars(query).all()
    return [request_data(r, include_private=user.role != "community") for r in rows]

@app.get("/api/requests/{request_id}/history")
def history(request_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    req = db.get(Request, request_id)
    if not req: raise HTTPException(404, "Solicitud no encontrada")
    ensure_request_access(req, user)
    events = [{"status":e.status,"detail":e.detail,"created_at":e.created_at.isoformat()} for e in db.scalars(select(RequestEvent).where(RequestEvent.request_id==request_id).order_by(RequestEvent.created_at)).all()]
    evidence = db.scalars(select(CollectionEvidence).where(CollectionEvidence.request_id == request_id).order_by(CollectionEvidence.created_at.desc())).all()
    return {"events": events, "evidence": [{"material_type":x.material_type,"weight_kg":x.weight_kg,"id":x.id,"photo_url":f"/api/evidence/{x.id}/photo","notes":x.notes,"created_at":x.created_at.isoformat()} for x in evidence]}

@app.get("/api/evidence/{evidence_id}/photo")
def evidence_photo(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    evidence = db.get(CollectionEvidence, evidence_id)
    if not evidence: raise HTTPException(404, "Evidencia no encontrada")
    req = db.get(Request, evidence.request_id)
    if not req: raise HTTPException(404, "Solicitud no encontrada")
    ensure_request_access(req, user)
    path = Path(evidence.photo_path)
    if not path.is_file(): raise HTTPException(404, "El archivo de evidencia no está disponible")
    return FileResponse(path)

@app.get("/api/collectors")
def collectors(db: Session = Depends(get_db), user: User = Depends(require_roles("coordinator_garden","coordinator_recycling","admin"))):
    role = "collector_garden" if user.role == "coordinator_garden" else "collector_recycling" if user.role == "coordinator_recycling" else None
    q = select(User).where(User.role == role, User.active.is_(True)) if role else select(User).where(User.role.in_(["collector_garden","collector_recycling"]), User.active.is_(True))
    return [user_data(u) for u in db.scalars(q).all()]

@app.post("/api/requests/{request_id}/assign")
def assign(request_id: int, data: AssignInput, db: Session = Depends(get_db), user: User = Depends(require_roles("coordinator_garden","coordinator_recycling","admin"))):
    req = db.get(Request, request_id); collector = db.get(User, data.collector_id)
    if not req: raise HTTPException(404, "Solicitud no encontrada")
    if req.status not in ("recibida", "asignada", "programada"):
        raise HTTPException(409, "No se puede asignar una solicitud cerrada o cancelada")
    if user.role == "coordinator_garden" and req.flow != "organico": raise HTTPException(403, "Flujo incorrecto")
    if user.role == "coordinator_recycling" and req.flow != "reciclable": raise HTTPException(403, "Flujo incorrecto")
    expected = "collector_garden" if req.flow == "organico" else "collector_recycling"
    if not collector or not collector.active or collector.role != expected: raise HTTPException(422, "El recolector no corresponde al flujo o está deshabilitado")
    req.collector_id=collector.id; req.coordinator_id=user.id; req.status="asignada"
    db.add(RequestEvent(request_id=req.id, actor_id=user.id, status=req.status, detail=f"Asignada a {collector.full_name}")); add_notification(db, collector.id, "Nueva recolección asignada", f"La solicitud {req.code} fue asignada a tu bandeja.", req.id); add_notification(db, user.id, "Asignación registrada", f"La solicitud {req.code} fue asignada a {collector.full_name}.", req.id); add_notification(db, req.user_id, "Tu solicitud fue asignada", f"La solicitud {req.code} fue asignada al equipo responsable.", req.id); notify_admins(db, "Solicitud asignada", f"{req.code}: asignada a {collector.full_name}.", req.id); db.commit()
    notify_whatsapp_users([collector], "Nueva recolección asignada", f"Código: {req.code}\nTipo: {req.flow}\nDirección: {req.address}\nIngresa a EcoConecta para consultar tu bandeja.")
    return {"message":"Asignación registrada", "request":request_data(req)}

@app.post("/api/requests/{request_id}/schedule")
def schedule(request_id: int, data: ScheduleInput, db: Session = Depends(get_db), user: User = Depends(require_roles("coordinator_garden","coordinator_recycling","admin"))):
    req=db.get(Request,request_id); collector=db.get(User,data.collector_id)
    if not req: raise HTTPException(404,"Solicitud no encontrada")
    if req.status not in ("recibida", "asignada", "programada"):
        raise HTTPException(409, "No se puede programar una solicitud cerrada o cancelada")
    if data.scheduled_date < date.today():
        raise HTTPException(422, "La fecha de recolección no puede estar en el pasado")
    if user.role == "coordinator_garden" and req.flow != "organico": raise HTTPException(403,"Flujo incorrecto")
    if user.role == "coordinator_recycling" and req.flow != "reciclable": raise HTTPException(403,"Flujo incorrecto")
    if not collector or not collector.active or collector.role != ("collector_garden" if req.flow=="organico" else "collector_recycling"): raise HTTPException(422,"Recolector no válido, deshabilitado o de otro flujo")
    req.collector_id=collector.id; req.coordinator_id=user.id; req.scheduled_date=data.scheduled_date; req.scheduled_time=data.scheduled_time; req.status="programada"
    db.add(RequestEvent(request_id=req.id,actor_id=user.id,status=req.status,detail=f"Programada para {data.scheduled_date} a las {data.scheduled_time.strftime('%H:%M')} con {collector.full_name}")); add_notification(db, collector.id, "Recolección programada", f"La solicitud {req.code} está programada para {data.scheduled_date} a las {data.scheduled_time.strftime('%H:%M')}.", req.id); add_notification(db, user.id, "Programación confirmada", f"La solicitud {req.code} quedó programada.", req.id); add_notification(db, req.user_id, "Tu recolección fue programada", f"La solicitud {req.code} está programada para {data.scheduled_date} a las {data.scheduled_time.strftime('%H:%M')}.", req.id); notify_admins(db, "Recolección programada", f"{req.code}: {data.scheduled_date} a las {data.scheduled_time.strftime('%H:%M')}.", req.id); db.commit()
    notify_whatsapp_users([collector], "Recolección programada", f"Código: {req.code}\nFecha: {data.scheduled_date}\nHora: {data.scheduled_time.strftime('%H:%M')}\nDirección: {req.address}")
    return {"message":"Programación confirmada", "request":request_data(req)}

@app.post("/api/requests/{request_id}/advance")
def advance_request(request_id: int, data: AdvanceInput, db: Session = Depends(get_db), user: User = Depends(require_roles("collector_garden","collector_recycling","admin"))):
    req = db.get(Request, request_id)
    if not req: raise HTTPException(404, "Solicitud no encontrada")
    if user.role != "admin" and req.collector_id != user.id: raise HTTPException(403, "Esta solicitud no está asignada a tu usuario")
    if user.role == "collector_garden" and req.flow != "organico": raise HTTPException(403, "No puedes gestionar solicitudes de otro colectivo")
    if user.role == "collector_recycling" and req.flow != "reciclable": raise HTTPException(403, "No puedes gestionar solicitudes de otro colectivo")
    transitions = {"programada": "en_camino", "en_camino": "recolectando"}
    expected = transitions.get(req.status)
    if data.status != expected: raise HTTPException(409, "El cambio de estado no corresponde al paso actual")
    req.status = data.status
    labels = {"en_camino": "El vehículo está en camino", "recolectando": "La recolección está en curso"}
    detail = (data.detail or labels[data.status]).strip()
    db.add(RequestEvent(request_id=req.id, actor_id=user.id, status=req.status, detail=detail))
    recipients = [req.coordinator_id] if req.coordinator_id else [u.id for u in staff_for_flow(db, req.flow)]
    for recipient in recipients: add_notification(db, recipient, labels[data.status], f"{req.code}: {detail}", req.id)
    add_notification(db, req.user_id, labels[data.status], f"{req.code}: {detail}", req.id)
    notify_admins(db, labels[data.status], f"{req.code}: {detail}", req.id)
    db.commit()
    staff_recipients = [db.get(User, recipient) for recipient in recipients if recipient]
    notify_whatsapp_users(staff_recipients, labels[data.status], f"Solicitud: {req.code}\n{detail}")
    return {"message": labels[data.status], "request": request_data(req)}

@app.post("/api/requests/{request_id}/collect")
def collect(request_id: int, weight_kg: float = Form(...), material_type: str = Form(...), photo: UploadFile = File(...), notes: str = Form(""), db: Session = Depends(get_db), user: User = Depends(require_roles("collector_garden","collector_recycling","admin"))):
    # Bloqueo de fila: evita que dos solicitudes concurrentes acrediten puntos dos veces.
    req = db.scalar(select(Request).where(Request.id == request_id).with_for_update())
    if not req: raise HTTPException(404, "Solicitud no encontrada")
    if user.role != "admin" and req.collector_id != user.id: raise HTTPException(403, "Esta solicitud no está asignada a tu usuario")
    if user.role == "collector_garden" and req.flow != "organico": raise HTTPException(403, "No puedes registrar recolecciones de otro colectivo")
    if user.role == "collector_recycling" and req.flow != "reciclable": raise HTTPException(403, "No puedes registrar recolecciones de otro colectivo")
    if req.status != "recolectando": raise HTTPException(409, "Primero debes iniciar la recolección")
    if weight_kg <= 0: raise HTTPException(422, "El peso debe ser mayor que cero")
    if material_type not in ("organico", "papel_carton", "plasticos", "vidrio", "metales", "mixto"):
        raise HTTPException(422, "Selecciona un tipo de material válido")

    ext = Path(photo.filename or "").suffix.lower()
    allowed = {
        ".jpg": ("image/jpeg",), ".jpeg": ("image/jpeg",),
        ".png": ("image/png",), ".webp": ("image/webp",)
    }
    if ext not in allowed or photo.content_type not in allowed.get(ext, ()):
        raise HTTPException(415, "Formato de imagen no permitido")

    # Lee en bloques y detiene la carga al superar 8 MiB; no escribe archivos ilimitados.
    max_bytes = 8 * 1024 * 1024
    filename = f"request_{req.id}_{uuid4().hex}{ext}"
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / filename
    total = 0
    header = b""
    try:
        with destination.open("xb") as buffer:
            while True:
                chunk = photo.file.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(413, "La fotografía no puede superar 8 MB")
                if len(header) < 16:
                    header += chunk[:16 - len(header)]
                buffer.write(chunk)
        signatures = {
            ".jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
            ".jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
            ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
            ".webp": lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP",
        }
        if total == 0 or not signatures[ext](header):
            raise HTTPException(415, "El contenido del archivo no corresponde a una imagen válida")

        points = round(weight_kg * settings.points_per_kg)
        owner = db.get(User, req.user_id)
        if not owner:
            raise HTTPException(500, "No se encontró el ciudadano asociado a la solicitud")
        req.weight_kg = weight_kg
        req.points_awarded = points
        req.status = "recolectada"
        req.collected_at = datetime.utcnow()
        owner.points += points
        db.add(CollectionEvidence(request_id=req.id, actor_id=user.id, material_type=material_type,
            weight_kg=weight_kg, photo_path=f"uploads/{filename}", notes=notes or None))
        db.add(RequestEvent(request_id=req.id, actor_id=user.id, status="recolectada",
            detail=f"Recolección finalizada: {weight_kg:g} kg de {material_type}. Evidencia fotográfica registrada. Se acreditaron {points} puntos."))
        recipients = [req.coordinator_id] if req.coordinator_id else [u.id for u in staff_for_flow(db, req.flow)]
        for recipient in recipients:
            add_notification(db, recipient, "Recolección finalizada",
                f"{req.code}: {weight_kg:g} kg registrados. Evidencia fotográfica guardada.", req.id)
        add_notification(db, req.user_id, "Recolección finalizada",
            f"{req.code}: se registraron {weight_kg:g} kg y se acreditaron {points} puntos.", req.id)
        notify_admins(db, "Recolección finalizada",
            f"{req.code}: {weight_kg:g} kg registrados; {points} puntos acreditados.", req.id)
        db.commit()
        staff_recipients = [db.get(User, recipient) for recipient in recipients if recipient]
        notify_whatsapp_users(staff_recipients, "Recolección finalizada", f"Solicitud: {req.code}\nPeso: {weight_kg:g} kg\nPuntos acreditados: {points}")
        return {"message":"Recolección finalizada; evidencia guardada y puntos acreditados", "points_awarded":points,"request":request_data(req)}
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    finally:
        photo.file.close()

@app.post("/api/chat")
def chat(data: ChatInput, request: HttpRequest):
    """Asistente local gratuito; no llama servicios externos ni requiere API key."""
    client_ip = request.client.host if request.client else "unknown"
    check_chat_rate_limit(client_ip)
    messages = []
    for item in data.messages[-10:]:
        if item.role not in ("user", "assistant"):
            raise HTTPException(422, "Formato de conversación no válido")
        messages.append({"role": item.role, "content": item.content.strip()[:2000]})
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(422, "Envía primero tu pregunta")
    result = answer_question(messages[-1]["content"], messages)
    return {"answer": result["answer"], "assistant": "EcoBot", "mode": "local_gratuito",
            "category": result["category"], "confidence": result["confidence"]}


@app.get("/api/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role not in ("community","coordinator_garden","coordinator_recycling","collector_garden","collector_recycling","admin"):
        raise HTTPException(403, "No tienes permisos para consultar notificaciones")
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50)).all()
    return [{"id":n.id,"request_id":n.request_id,"title":n.title,"message":n.message,"read":n.read,"created_at":n.created_at.isoformat()} for n in rows]

@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.get(Notification, notification_id)
    if not item: raise HTTPException(404, "Notificación no encontrada")
    if item.user_id != user.id: raise HTTPException(403, "No puedes modificar esta notificación")
    item.read = True; db.commit()
    return {"message":"Notificación marcada como leída"}

@app.post("/api/requests/{request_id}/cancel")
def cancel(request_id: int, db: Session=Depends(get_db), user: User=Depends(current_user)):
    req=db.get(Request,request_id)
    if not req: raise HTTPException(404,"Solicitud no encontrada")
    if user.role == "community":
        if req.user_id != user.id:
            raise HTTPException(403, "Solo puedes cancelar tus propias solicitudes")
    elif user.role == "coordinator_garden":
        if req.flow != "organico": raise HTTPException(403, "No puedes cancelar solicitudes de otro colectivo")
    elif user.role == "coordinator_recycling":
        if req.flow != "reciclable": raise HTTPException(403, "No puedes cancelar solicitudes de otro colectivo")
    elif user.role != "admin":
        raise HTTPException(403, "Tu perfil no tiene permiso para cancelar solicitudes")
    if req.status=="recolectada": raise HTTPException(409,"No se puede cancelar una recolección cerrada")
    if req.status=="cancelada": raise HTTPException(409,"La solicitud ya está cancelada")
    req.status="cancelada"
    db.add(RequestEvent(request_id=req.id,actor_id=user.id,status="cancelada",detail="Solicitud cancelada"))
    add_notification(db, req.user_id, "Solicitud cancelada", f"La solicitud {req.code} fue cancelada.", req.id)
    recipients = []
    if req.coordinator_id:
        coordinator = db.get(User, req.coordinator_id)
        if coordinator and coordinator.active:
            recipients.append(coordinator)
    else:
        recipients.extend(staff_for_flow(db, req.flow))
    if req.collector_id:
        assigned_collector = db.get(User, req.collector_id)
        if assigned_collector and assigned_collector.active:
            recipients.append(assigned_collector)
    recipients = list({recipient.id: recipient for recipient in recipients}.values())
    for recipient in recipients:
        add_notification(db, recipient.id, "Solicitud cancelada", f"{req.code}: la solicitud fue cancelada.", req.id)
    notify_admins(db, "Solicitud cancelada", f"{req.code}: solicitud cancelada.", req.id)
    db.commit()
    notify_whatsapp_users(recipients + admins_for_notifications(db), "Solicitud cancelada", f"Solicitud: {req.code}\nLa solicitud fue cancelada.")
    return {"message":"Solicitud cancelada"}

@app.get("/api/dashboard")
def dashboard(db: Session=Depends(get_db), user: User=Depends(require_roles("coordinator_garden","coordinator_recycling","collector_garden","collector_recycling","admin"))):
    q=select(Request)
    if user.role=="coordinator_garden": q=q.where(Request.flow=="organico")
    if user.role=="coordinator_recycling": q=q.where(Request.flow=="reciclable")
    if user.role in ("collector_garden","collector_recycling"): q=q.where(Request.collector_id==user.id)
    rows=db.scalars(q).all()
    return {"total":len(rows),"recibidas":sum(r.status=="recibida" for r in rows),"asignadas":sum(r.status=="asignada" for r in rows),"programadas":sum(r.status=="programada" for r in rows),"en_camino":sum(r.status=="en_camino" for r in rows),"recolectando":sum(r.status=="recolectando" for r in rows),"recolectadas":sum(r.status=="recolectada" for r in rows),"canceladas":sum(r.status=="cancelada" for r in rows),"kg":round(sum(r.weight_kg or 0 for r in rows),2),"points":sum(r.points_awarded for r in rows)}

@app.get("/api/leaderboard")
def leaderboard(db: Session=Depends(get_db), user: User=Depends(current_user)):
    return [{"name":u.full_name,"points":u.points} for u in db.scalars(select(User).where(User.role=="community").order_by(User.points.desc()).limit(10)).all()]
