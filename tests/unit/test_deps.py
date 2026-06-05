"""Pruebas unitarias de las dependencias de FastAPI (app/api/deps.py).

Se llaman las funciones directamente (sin servidor HTTP), pasándoles repos reales sobre
SQLite en memoria y tokens generados a mano.
"""

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.application.schemas.user import UserCreate
from app.application.services.auth_service import AuthService
from app.core.config import settings
from app.core.security import create_access_token
from app.domain.entities.user import Role, User
from app.infrastructure.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository


def _repo_con_usuario(
    db_session: Session, email: str = "u@x.com", role: Role = Role.CLIENTE
) -> SqlAlchemyUserRepository:
    repo = SqlAlchemyUserRepository(db_session)
    AuthService(repo).register(
        UserCreate(email=email, password="Secreta123!", full_name="Usuario"), role=role
    )
    return repo


# get_current_user() devuelve el usuario cuando el token es válido.
def test_get_current_user_valido(db_session: Session) -> None:
    repo = _repo_con_usuario(db_session)
    token = create_access_token(subject="u@x.com", role="cliente")
    user = deps.get_current_user(token=token, repo=repo)
    assert user.email == "u@x.com"


# get_current_user() con un token corrupto lanza 401.
def test_get_current_user_token_invalido(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(token="token-basura", repo=repo)
    assert exc.value.status_code == 401


# get_current_user() con un token sin 'sub' lanza 401.
def test_get_current_user_sin_sub(db_session: Session) -> None:
    token = jwt.encode({"role": "cliente"}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    repo = SqlAlchemyUserRepository(db_session)
    with pytest.raises(HTTPException):
        deps.get_current_user(token=token, repo=repo)


# get_current_user() de un usuario que no existe lanza 401.
def test_get_current_user_usuario_inexistente(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    token = create_access_token(subject="nadie@x.com", role="cliente")
    with pytest.raises(HTTPException):
        deps.get_current_user(token=token, repo=repo)


# require_admin() permite a un administrador y rechaza (403) a un cliente.
def test_require_admin(db_session: Session) -> None:
    admin = User(email="a@x.com", hashed_password="h", full_name="A", role=Role.ADMIN)
    assert deps.require_admin(admin) is admin

    cliente = User(email="c@x.com", hashed_password="h", full_name="C", role=Role.CLIENTE)
    with pytest.raises(HTTPException) as exc:
        deps.require_admin(cliente)
    assert exc.value.status_code == 403


# get_optional_user(): sin token -> None; token válido -> usuario; token inválido -> None.
def test_get_optional_user(db_session: Session) -> None:
    repo = _repo_con_usuario(db_session, email="opt@x.com")
    assert deps.get_optional_user(token=None, repo=repo) is None

    token = create_access_token(subject="opt@x.com", role="cliente")
    found = deps.get_optional_user(token=token, repo=repo)
    assert found is not None
    assert found.email == "opt@x.com"

    assert deps.get_optional_user(token="basura", repo=repo) is None


# Las factories devuelven instancias válidas de repos y servicios.
def test_factories(db_session: Session) -> None:
    user_repo = deps.get_user_repository(db_session)
    product_repo = deps.get_product_repository(db_session)
    assert deps.get_auth_service(user_repo) is not None
    assert deps.get_product_service(product_repo) is not None
    assert deps.get_order_service(db_session) is not None
