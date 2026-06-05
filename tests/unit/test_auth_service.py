"""Pruebas unitarias del servicio de auth usando un repositorio falso en memoria.

Demuestra el valor del patrón Repository: el servicio se prueba sin base de datos.
"""

import pytest

from app.application.errors import EmailAlreadyExistsError, InvalidCredentialsError
from app.application.schemas.user import UserCreate
from app.application.services.auth_service import AuthService
from app.domain.entities.user import Role, User
from app.domain.repositories.user_repository import UserRepository


# Repositorio falso que almacena usuarios en memoria, sin persistencia.
class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._by_email: dict[str, User] = {}
        self._seq = 0

    # Implementación de los métodos del repositorio, usando un diccionario
    # para simular la base de datos.
    def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)  #

    def get_by_id(self, user_id: int) -> User | None:
        return next(
            (u for u in self._by_email.values() if u.id == user_id), None
        )  # Busca el usuario por ID recorriendo los valores del diccionario.

    def add(self, user: User) -> User:
        self._seq += 1
        user.id = self._seq
        self._by_email[user.email] = user
        return user


# Fixture para crear una instancia del servicio de auth con el repositorio falso.
@pytest.fixture
def service() -> AuthService:
    return AuthService(FakeUserRepository())


# Helper para crear un nuevo usuario de prueba.
def _new_user() -> UserCreate:
    return UserCreate(email="Cliente@X.com", password="Secreta123!", full_name="Cliente Uno")


# Se debe poder registrar un nuevo usuario con un correo y contraseña válidos,
# y el password debe almacenarse hasheado.
def test_register_creates_user_with_hashed_password(service: AuthService) -> None:
    user = service.register(_new_user())
    assert user.id is not None
    assert user.email == "cliente@x.com"  # normalizado a minúsculas
    assert user.role == Role.CLIENTE
    assert user.hashed_password != "Secreta123!"


# Se debe poder registrar un usuario con un rol específico, como ADMIN.
def test_register_with_admin_role(service: AuthService) -> None:
    user = service.register(_new_user(), role=Role.ADMIN)
    assert user.role == Role.ADMIN


# No se debe permitir registrar un usuario con un correo que ya existe.
def test_register_duplicate_email_raises(service: AuthService) -> None:
    service.register(_new_user())
    with pytest.raises(EmailAlreadyExistsError):
        service.register(_new_user())


# Un usuario con credenciales válidas debe poder autenticarse correctamente.
def test_authenticate_valid_credentials(service: AuthService) -> None:
    service.register(_new_user())
    user = service.authenticate("cliente@x.com", "Secreta123!")
    assert user.email == "cliente@x.com"


# Una contraseña incorrecta no debe permitir autenticarse, aunque el correo sea correcto.
def test_authenticate_wrong_password_raises(service: AuthService) -> None:
    service.register(_new_user())
    with pytest.raises(InvalidCredentialsError):
        service.authenticate("cliente@x.com", "incorrecta")


# Un correo desconocido no debe poder autenticarse, aunque la contraseña sea correcta.
def test_authenticate_unknown_email_raises(service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        service.authenticate("nadie@x.com", "Secreta123!")


# Un usuario inactivo no debe poder autenticarse, aunque su correo y contraseña sean correctos.
def test_authenticate_inactive_user_raises() -> None:
    repo = FakeUserRepository()
    service = AuthService(repo)
    user = service.register(_new_user())
    user.is_active = False
    with pytest.raises(InvalidCredentialsError):
        service.authenticate("cliente@x.com", "Secreta123!")
