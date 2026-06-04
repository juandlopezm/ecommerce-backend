"""Fixtures de pruebas.

Por defecto usan SQLite en memoria (rápido). Si se define la variable de entorno
``TEST_DATABASE_URL`` (p. ej. apuntando a PostgreSQL), la misma suite se ejecuta contra esa
base de datos real — así probamos la integración con la BD de producción (RNF-08.2).
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.limiter import limiter

# Importa el modelo para registrar la tabla en la metadata.
from app.infrastructure.models.user_model import UserModel  # noqa: F401
from app.main import app


def _reset_limiter() -> None:
    try:
        limiter.reset()
    except Exception:  # pragma: no cover - depende de la versión de slowapi
        pass


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    """Engine de prueba.

    - Sin ``TEST_DATABASE_URL``: SQLite en memoria (StaticPool, una sola conexión).
    - Con ``TEST_DATABASE_URL``: base de datos real (p. ej. PostgreSQL) para integración.
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if test_db_url:
        eng = create_engine(test_db_url)
    else:
        eng = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Sesión directa a la base de datos de prueba (para preparar datos)."""
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine: Engine) -> Generator[TestClient, None, None]:
    """Cliente HTTP con ``get_db`` sobreescrito para usar la base de datos en memoria."""
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Por defecto, prácticamente sin límite para no interferir entre pruebas.
    settings.login_rate_limit = "1000/minute"
    _reset_limiter()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    settings.login_rate_limit = "1000/minute"
    _reset_limiter()


@pytest.fixture
def admin_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    """Crea un administrador y devuelve el header Authorization con su token."""
    from app.application.schemas.user import UserCreate
    from app.application.services.auth_service import AuthService
    from app.domain.entities.user import Role
    from app.infrastructure.repositories.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    AuthService(SqlAlchemyUserRepository(db_session)).register(
        UserCreate(email="admin@x.com", password="Admin123!", full_name="Admin"),
        role=Role.ADMIN,
    )
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@x.com", "password": "Admin123!"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_product(db_session: Session):
    """Factory que inserta un producto en la base de datos de prueba."""
    from decimal import Decimal

    from app.domain.entities.product import Product
    from app.infrastructure.repositories.sqlalchemy_product_repository import (
        SqlAlchemyProductRepository,
    )

    repo = SqlAlchemyProductRepository(db_session)

    def _make(**overrides: object) -> Product:
        data: dict = {
            "name": "Labial",
            "price": Decimal("10000"),
            "stock": 5,
            "brand": "NYX",
            "category": "Maquillaje",
        }
        data.update(overrides)
        return repo.add(Product(**data))

    return _make
