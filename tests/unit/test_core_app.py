"""Pruebas unitarias de piezas del core/app: get_db, _engine_kwargs y el handler de rate limit."""

import pytest
from sqlalchemy.orm import Session

from app.core.database import _engine_kwargs, get_db
from app.main import _rate_limit_handler


# get_db() debe entregar una Session y, al agotar el generador, cerrarla (bloque finally).
def test_get_db_yields_session_and_closes() -> None:
    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    gen.close()  # dispara el finally que cierra la sesión
    with pytest.raises(StopIteration):
        next(gen)  # el generador ya no produce más sesiones


# _engine_kwargs con una URL de SQLite usa check_same_thread=False (rama 'if sqlite').
def test_engine_kwargs_for_sqlite() -> None:
    assert _engine_kwargs("sqlite:///./x.db") == {"connect_args": {"check_same_thread": False}}


# _engine_kwargs con una URL de PostgreSQL usa pool_pre_ping (rama 'else').
def test_engine_kwargs_for_postgres() -> None:
    assert _engine_kwargs("postgresql+psycopg://u:p@host/db") == {"pool_pre_ping": True}


# _rate_limit_handler() debe responder con código 429 cuando se supera el límite.
def test_rate_limit_handler_returns_429() -> None:
    response = _rate_limit_handler(None, Exception("demasiados intentos"))  # type: ignore[arg-type]
    assert response.status_code == 429
