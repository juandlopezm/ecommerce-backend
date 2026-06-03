"""Endpoints de autenticación (RF-07): registro, login y perfil del usuario actual."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_service, get_current_user
from app.application.errors import EmailAlreadyExistsError, InvalidCredentialsError
from app.application.schemas.auth import Token
from app.application.schemas.user import UserCreate, UserRead
from app.application.services.auth_service import AuthService
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import create_access_token
from app.domain.entities.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Registra un usuario nuevo (rol cliente). Rechaza emails duplicados (HU-11)."""
    try:
        user = service.register(data)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        ) from exc
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
@limiter.limit(lambda: settings.login_rate_limit)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> Token:
    """Inicia sesión y devuelve un JWT (HU-12). Con rate limiting de intentos (RNF-02.7)."""
    try:
        user = service.authenticate(form_data.username, form_data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token = create_access_token(subject=user.email, role=user.role.value)
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Devuelve los datos del usuario autenticado."""
    return UserRead.model_validate(current_user)
