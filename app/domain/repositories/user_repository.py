"""Interfaz (puerto) del repositorio de usuarios — patrón Repository.

Abstrae el acceso a datos: la capa de aplicación depende de esta interfaz, no de SQLAlchemy.
Esto permite inyectar implementaciones falsas/in-memory en las pruebas (DI + mocks).
"""

from abc import ABC, abstractmethod

from app.domain.entities.user import User


class UserRepository(ABC):
    """Contrato de persistencia de usuarios."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Devuelve el usuario con ese email, o ``None`` si no existe."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Devuelve el usuario con ese id, o ``None`` si no existe."""

    @abstractmethod
    def add(self, user: User) -> User:
        """Persiste un usuario nuevo y lo devuelve con su ``id`` asignado."""
