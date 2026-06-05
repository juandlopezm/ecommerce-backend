"""Pruebas unitarias de piezas del core/app: la dependencia get_db y el handler de rate limit."""

from app.core.database import get_db
from app.main import _rate_limit_handler


# get_db() debe entregar una sesión y cerrarla al agotar el generador (finally).
def test_get_db_genera_y_cierra() -> None:
    gen = get_db()
    session = next(gen)
    assert session is not None
    gen.close()  # dispara el bloque finally que cierra la sesión


# _rate_limit_handler() debe responder con código 429 cuando se supera el límite.
def test_rate_limit_handler_devuelve_429() -> None:
    response = _rate_limit_handler(None, Exception("demasiados intentos"))  # type: ignore[arg-type]
    assert response.status_code == 429
