from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(value: str) -> str:
    return pwd.hash(value)

def verify_password(value: str, hashed: str) -> bool:
    return pwd.verify(value, hashed)

def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, settings.secret_key, algorithm="HS256")

def current_user(token: str = Depends(oauth), db: Session = Depends(get_db)) -> User:
    error = HTTPException(status_code=401, detail="Sesión no válida")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except (JWTError, KeyError, ValueError):
        raise error
    if not user or not user.active:
        raise error
    return user

def require_roles(*roles):
    def check(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
        return user
    return check
