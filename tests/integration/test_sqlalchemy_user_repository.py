"""Pruebas de integración del repositorio de usuarios sobre SQLAlchemy (SQLite en memoria).

Usa el fixture ``db_session`` (definido en tests/conftest.py) que crea una base de datos
en memoria con las tablas ya creadas, sin tocar la base real.
"""

from sqlalchemy.orm import Session

from app.domain.entities.user import Role, User
from app.infrastructure.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository


def _user(email: str = "a@x.com") -> User:
    return User(email=email, hashed_password="hash", full_name="Usuario", role=Role.CLIENTE)


# add() debe persistir el usuario y asignarle un id autoincremental.
def test_add_asigna_id(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = repo.add(_user())
    assert user.id is not None


# get_by_email() debe devolver el usuario guardado, ya mapeado a la entidad de dominio.
def test_get_by_email_encuentra(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    repo.add(_user("ana@x.com"))
    found = repo.get_by_email("ana@x.com")
    assert found is not None
    assert found.email == "ana@x.com"
    assert found.role == Role.CLIENTE


# get_by_email() con un correo que no existe debe devolver None.
def test_get_by_email_inexistente(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    assert repo.get_by_email("nadie@x.com") is None


# get_by_id() debe encontrar al usuario por su id, y devolver None si no existe.
def test_get_by_id(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    created = repo.add(_user("x@x.com"))
    assert created.id is not None
    found = repo.get_by_id(created.id)
    assert found is not None
    assert found.email == "x@x.com"
    assert repo.get_by_id(9999) is None
