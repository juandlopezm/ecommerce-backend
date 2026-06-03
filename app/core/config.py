"""Configuración de la aplicación leída de variables de entorno (Pydantic Settings)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de configuración del backend.

    Los valores se leen de variables de entorno (o de un archivo ``.env``). Los nombres
    de las variables son insensibles a mayúsculas (p. ej. ``DATABASE_URL`` -> ``database_url``).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de datos. Por defecto SQLite local para arrancar sin Docker; en desarrollo/producción
    # se usa PostgreSQL definiendo DATABASE_URL.
    database_url: str = "sqlite:///./ecommerce.db"

    # Seguridad / JWT
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Rate limiting del login (formato de slowapi, p. ej. "5/minute")
    login_rate_limit: str = "5/minute"

    # Credenciales del administrador inicial (sembrado vía `python -m app.seed`)
    admin_email: str = "admin@ecommerce.com"
    admin_password: str = "Admin123!"
    admin_full_name: str = "Administrador"


settings = Settings()
