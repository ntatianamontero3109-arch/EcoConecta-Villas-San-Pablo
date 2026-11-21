"""Crea una cuenta interna desde la consola del servidor; nunca expone roles en el registro web."""
from getpass import getpass
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User
from app.security import hash_password

ROLES = {
    "admin",
    "coordinator_garden",
    "coordinator_recycling",
    "collector_garden",
    "collector_recycling",
}


def main():
    print("Alta administrativa local de EcoConecta")
    role = input("Rol (" + ", ".join(sorted(ROLES)) + "): ").strip()
    if role not in ROLES:
        raise SystemExit("Rol no permitido.")
    name = input("Nombre completo: ").strip()
    phone = input("Teléfono: ").strip()
    password = getpass("Contraseña (mínimo 12 caracteres): ")
    confirm = getpass("Repite la contraseña: ")
    if len(name) < 3 or len(phone) < 7:
        raise SystemExit("Nombre o teléfono no válido.")
    if len(password) < 12 or password != confirm:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres y coincidir.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.phone == phone)):
            raise SystemExit("Ya existe una cuenta con ese teléfono.")
        user = User(full_name=name, phone=phone, password_hash=hash_password(password), role=role, active=True)
        db.add(user)
        db.commit()
        print(f"Cuenta creada: ID {user.id}, rol {user.role}. No se mostró ni guardó la contraseña en texto plano.")


if __name__ == "__main__":
    main()
