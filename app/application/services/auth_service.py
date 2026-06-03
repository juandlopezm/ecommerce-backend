"""Servicio de autenticación: casos de uso de registro y login (RF-07).

Depende únicamente de la interfaz ``UserRepository`` (no de SQLAlchemy), lo que permite
probarlo con un repositorio falso en memoria.
"""

from app.application.errors import EmailAlreadyExistsError, InvalidCredentialsError
from app.application.schemas.user import UserCreate
from app.core.security import hash_password, verify_password
from app.domain.entities.user import Role, User
from app.domain.repositories.user_repository import UserRepository


class AuthService:
    """Reglas de negocio de usuarios y autenticación."""

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def register(self, data: UserCreate, role: Role = Role.CLIENTE) -> User:
        """Registra un usuario nuevo. Rechaza emails duplicados (HU-11)."""
        normalized_email = data.email.lower()
        if self._repository.get_by_email(normalized_email) is not None:
            raise EmailAlreadyExistsError(normalized_email)

        user = User(
            email=normalized_email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=role,
        )
        return self._repository.add(user)

    def authenticate(self, email: str, password: str) -> User:
        """Valida credenciales; devuelve el usuario o lanza InvalidCredentialsError (HU-12)."""
        user = self._repository.get_by_email(email.lower())
        if user is None or not user.is_active:
            raise InvalidCredentialsError(email)
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError(email)
        return user
