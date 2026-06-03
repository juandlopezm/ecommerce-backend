"""Fixtures de pruebas: base de datos SQLite en memoria y cliente HTTP de FastAPI."""

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
    """Engine SQLite en memoria compartido (StaticPool mantiene una única conexión)."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
