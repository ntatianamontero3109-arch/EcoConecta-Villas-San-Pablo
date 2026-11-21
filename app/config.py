from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EcoConecta"
    # No se permite una clave predeterminada: debe venir del entorno.
    secret_key: str
    database_url: str = "postgresql+psycopg://ecoconecta:ecoconecta@db:5432/ecoconecta"
    access_token_minutes: int = 720
    points_per_kg: float = 1.0
    environment: str = "development"
    whatsapp_enabled: bool = False
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = ""
    whatsapp_template_name: str = ""
    whatsapp_template_language: str = "es_CO"
    # Lista explícita de números con consentimiento para recibir WhatsApp, separados por coma.
    whatsapp_allowed_recipients: str = ""

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        if value.lower() in {"development-only-change-me", "change-this-to-a-long-random-secret"}:
            raise ValueError("Debes reemplazar la SECRET_KEY de ejemplo")
        return value

    @field_validator("access_token_minutes")
    @classmethod
    def validate_token_duration(cls, value: int) -> int:
        if value < 5 or value > 1440:
            raise ValueError("ACCESS_TOKEN_MINUTES debe estar entre 5 y 1440")
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
