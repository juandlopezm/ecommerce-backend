"""Pruebas de integración de los endpoints de autenticación (HU-11, HU-12, HU-13, RNF-02.7)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.schemas.user import UserCreate
from app.application.services.auth_service import AuthService
from app.core.config import settings
from app.core.limiter import limiter
from app.domain.entities.user import Role
from app.infrastructure.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
ADMIN_URL = "/api/v1/admin/ping"

VALID_USER = {"email": "ana@x.com", "password": "Secreta123!", "full_name": "Ana Pérez"}


def _register(client: TestClient, **overrides: str) -> None:
    payload = {**VALID_USER, **overrides}
    client.post(REGISTER_URL, json=payload)


def _login_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post(LOGIN_URL, data={"username": email, "password": password})
    return resp.json()["access_token"]


# --- Registro (HU-11) ---------------------------------------------------------------------


def test_register_returns_201_and_public_fields(client: TestClient) -> None:
    resp = client.post(REGISTER_URL, json=VALID_USER)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "ana@x.com"
    assert body["role"] == Role.CLIENTE.value
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    client.post(REGISTER_URL, json=VALID_USER)
    resp = client.post(REGISTER_URL, json=VALID_USER)
    assert resp.status_code == 409


def test_register_invalid_payload_returns_422(client: TestClient) -> None:
    resp = client.post(
        REGISTER_URL, json={"email": "no-es-email", "password": "x", "full_name": ""}
    )
    assert resp.status_code == 422


# --- Login (HU-12) ------------------------------------------------------------------------


def test_login_valid_returns_token(client: TestClient) -> None:
    _register(client)
    resp = client.post(LOGIN_URL, data={"username": "ana@x.com", "password": "Secreta123!"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_invalid_credentials_returns_401(client: TestClient) -> None:
    _register(client)
    resp = client.post(LOGIN_URL, data={"username": "ana@x.com", "password": "incorrecta"})
    assert resp.status_code == 401


# --- Perfil (/me) -------------------------------------------------------------------------


def test_me_with_valid_token(client: TestClient) -> None:
    _register(client)
    token = _login_token(client, "ana@x.com", "Secreta123!")
    resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "ana@x.com"


def test_me_without_token_returns_401(client: TestClient) -> None:
    resp = client.get(ME_URL)
    assert resp.status_code == 401


# --- Panel admin (HU-13) ------------------------------------------------------------------


def test_admin_ping_allows_admin(client: TestClient, db_session: Session) -> None:
    AuthService(SqlAlchemyUserRepository(db_session)).register(
        UserCreate(email="admin@x.com", password="Admin123!", full_name="Admin"),
        role=Role.ADMIN,
    )
    token = _login_token(client, "admin@x.com", "Admin123!")
    resp = client.get(ADMIN_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "pong"


def test_admin_ping_forbidden_for_client(client: TestClient) -> None:
    _register(client)
    token = _login_token(client, "ana@x.com", "Secreta123!")
    resp = client.get(ADMIN_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# --- Rate limiting (RNF-02.7 / HU-12) -----------------------------------------------------


def test_login_rate_limit_returns_429(client: TestClient) -> None:
    _register(client)
    settings.login_rate_limit = "3/minute"
    limiter.reset()

    statuses = [
        client.post(LOGIN_URL, data={"username": "ana@x.com", "password": "incorrecta"}).status_code
        for _ in range(5)
    ]

    assert statuses[:3] == [401, 401, 401]
    assert 429 in statuses[3:]
