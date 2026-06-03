"""Dependencias de FastAPI (inyección de dependencias): repositorio, servicio y usuario actual."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.application.services.auth_service import AuthService
from app.application.services.product_service import ProductService
from app.core.database import get_db
from app.core.security import decode_token
from app.domain.entities.user import Role, User
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)
from app.infrastructure.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(db)


def get_auth_service(repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(repo)


def get_product_repository(db: Session = Depends(get_db)) -> ProductRepository:
    return SqlAlchemyProductRepository(db)


def get_product_service(
    repo: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    return ProductService(repo)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Decodifica el JWT y devuelve el usuario autenticado, o 401 si es inválido."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise _credentials_exc from exc

    email = payload.get("sub")
    if not email:
        raise _credentials_exc

    user = repo.get_by_email(email)
    if user is None or not user.is_active:
        raise _credentials_exc
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Restringe el acceso a administradores (RF-07.6 / RF-08.1 / HU-13)."""
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a administradores",
        )
    return user
