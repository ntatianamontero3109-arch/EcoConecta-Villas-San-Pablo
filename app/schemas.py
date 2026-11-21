from datetime import date, time
from pydantic import BaseModel, Field, field_validator

class RegisterInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    password: str = Field(min_length=8, max_length=100)
    email: str | None = None
    address: str | None = None
    generator_type: str = "hogar"

    @field_validator("full_name", "phone")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio")
        return value

    @field_validator("password")
    @classmethod
    def bcrypt_password_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Correo electrónico no válido")
        return value

class LoginInput(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return value.strip()

    @field_validator("password")
    @classmethod
    def bcrypt_password_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Credenciales no válidas")
        return value

class RequestInput(BaseModel):
    generator_type: str
    waste_type: str
    address: str = Field(min_length=5, max_length=240)
    notes: str | None = None
    preferred_time: str | None = None

    @field_validator("generator_type", "waste_type", "address")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío")
        return value

class AssignInput(BaseModel):
    collector_id: int

class ScheduleInput(BaseModel):
    scheduled_date: date
    scheduled_time: time
    collector_id: int

class CloseInput(BaseModel):
    weight_kg: float = Field(gt=0)


class AdvanceInput(BaseModel):
    status: str
    detail: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=2000)

class ChatInput(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=12)


class AdminUserUpdate(BaseModel):
    role: str | None = None
    active: bool | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        allowed = {"community", "coordinator_garden", "coordinator_recycling", "collector_garden", "collector_recycling", "admin"}
        if value is not None and value not in allowed:
            raise ValueError("Rol no válido")
        return value
