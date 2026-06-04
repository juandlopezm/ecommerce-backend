"""Utilidades de seguridad: hash de contraseñas (bcrypt) y tokens JWT (OAuth2).

Se usa ``bcrypt`` directamente (en lugar de passlib) y ``PyJWT`` por compatibilidad con
versiones recientes de Python. Cumple RNF-02.1 (hash seguro) y RNF-02.2 (JWT con expiración).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt opera sobre, como máximo, 72 bytes. Truncamos de forma explícita para evitar errores
# con contraseñas muy largas, manteniendo un comportamiento determinista.
_BCRYPT_MAX_BYTES = 72


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Genera un JWT firmado con el ``subject`` (email), el ``role`` y la expiración."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza ``jwt.PyJWTError`` si es inválido o expiró."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
