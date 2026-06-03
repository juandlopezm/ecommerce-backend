"""Implementación del ``UserRepository`` sobre SQLAlchemy."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import Role, User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.models.user_model import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        hashed_password=model.hashed_password,
        full_name=model.full_name,
        role=Role(model.role),
        is_active=model.is_active,
    )


class SqlAlchemyUserRepository(UserRepository):
    """Repositorio de usuarios respaldado por una sesión SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _to_entity(model) if model else None

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    def add(self, user: User) -> User:
        model = UserModel(
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)
