"""Schemas Pydantic para usuarios (validación y serialización)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities.user import Role


class UserCreate(BaseModel):
    """Datos de entrada para registrar un usuario (RF-07.1)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserRead(BaseModel):
    """Representación pública de un usuario (sin la contraseña)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
