"""Pruebas unitarias de las utilidades de seguridad (hash y JWT)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext() -> None:
    hashed = hash_password("Secreta123!")
    assert hashed != "Secreta123!"
    assert hashed.startswith("$2")  # prefijo bcrypt


def test_verify_password_correct_and_incorrect() -> None:
    hashed = hash_password("Secreta123!")
    assert verify_password("Secreta123!", hashed) is True
    assert verify_password("incorrecta", hashed) is False


def test_token_round_trip_contains_subject_and_role() -> None:
    token = create_access_token(subject="user@x.com", role="administrador")
    payload = decode_token(token)
    assert payload["sub"] == "user@x.com"
    assert payload["role"] == "administrador"


def test_expired_token_raises() -> None:
    token = create_access_token(
        subject="user@x.com",
        role="cliente",
        expires_delta=timedelta(minutes=-1),
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_verify_password_returns_false_for_malformed_hash() -> None:
    # Rama except (ValueError/TypeError): un hash inválido no debe romper, devuelve False.
    assert verify_password("Secreta123!", "esto-no-es-un-hash-bcrypt") is False


def test_password_longer_than_72_bytes_is_truncated() -> None:
    # bcrypt sólo usa los primeros 72 bytes (rama de truncado de _encode): dos contraseñas que
    # comparten esos 72 bytes deben validar contra el mismo hash.
    base = "x" * 72
    longer = base + "estos-bytes-extra-se-ignoran"
    hashed = hash_password(longer)
    assert verify_password(longer, hashed) is True
    assert verify_password(base, hashed) is True


def test_empty_password_can_be_hashed_and_verified() -> None:
    # Edge: contraseña vacía. Debe hashear y validar, y rechazar una distinta.
    hashed = hash_password("")
    assert verify_password("", hashed) is True
    assert verify_password("x", hashed) is False


def test_zero_expiry_is_respected_not_replaced_by_default() -> None:
    # Regresión: con expires_delta=timedelta(0) la expiración debe ser ~ahora (no ~60 min).
    # Antes fallaba por usar `expires_delta or default` (timedelta(0) es falsy); ya corregido
    # con un `is None` explícito. Se revisa el claim 'exp' sin validar la expiración.
    token = create_access_token(subject="u@x.com", role="cliente", expires_delta=timedelta(0))
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": False},
    )
    exp = datetime.fromtimestamp(payload["exp"], UTC)
    assert (exp - datetime.now(UTC)) < timedelta(minutes=1)
