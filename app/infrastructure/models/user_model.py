"""Modelo ORM (tabla ``users``) de SQLAlchemy."""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.entities.user import Role


class UserModel(Base):
    """Tabla de usuarios."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=Role.CLIENTE.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
