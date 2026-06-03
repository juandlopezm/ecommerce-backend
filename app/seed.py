"""Siembra el usuario administrador inicial (RF-08.1).

Uso:  python -m app.seed

Idempotente: si el administrador ya existe, no hace nada. Lee las credenciales de las
variables de entorno ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_FULL_NAME.
"""

from app.application.schemas.user import UserCreate
from app.application.services.auth_service import AuthService
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.domain.entities.user import Role

# Importa el modelo para registrarlo en la metadata antes de create_all.
from app.infrastructure.models.user_model import UserModel  # noqa: F401
from app.infrastructure.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository


def seed_admin() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        repo = SqlAlchemyUserRepository(session)
        if repo.get_by_email(settings.admin_email.lower()) is not None:
            print(f"El administrador '{settings.admin_email}' ya existe. Nada que sembrar.")
            return

        service = AuthService(repo)
        service.register(
            UserCreate(
                email=settings.admin_email,
                password=settings.admin_password,
                full_name=settings.admin_full_name,
            ),
            role=Role.ADMIN,
        )
        print(f"Administrador '{settings.admin_email}' creado correctamente.")
    finally:
        session.close()


if __name__ == "__main__":
    seed_admin()
