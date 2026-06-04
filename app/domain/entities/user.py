"""Entidad de dominio Usuario y roles. Independiente de la capa de persistencia."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """Roles del sistema (RF-07.5)."""

    CLIENTE = "cliente"
    INVITADO = "invitado"
    ADMIN = "administrador"


@dataclass
class User:
    """Usuario del dominio. La contraseña se almacena siempre como hash."""

    email: str
    hashed_password: str
    full_name: str
    role: Role = Role.CLIENTE
    is_active: bool = True
    id: int | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN
