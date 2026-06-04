"""Pruebas unitarias de las utilidades de seguridad (hash y JWT)."""

from datetime import timedelta

import jwt
import pytest

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
