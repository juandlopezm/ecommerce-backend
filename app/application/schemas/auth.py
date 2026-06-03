"""Schemas Pydantic para autenticación."""

from pydantic import BaseModel


class Token(BaseModel):
    """Token de acceso devuelto al iniciar sesión (RF-07.1 / HU-12)."""

    access_token: str
    token_type: str = "bearer"
