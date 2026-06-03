"""Excepciones de la capa de aplicación (independientes de HTTP)."""


class ApplicationError(Exception):
    """Base de los errores de negocio."""


class EmailAlreadyExistsError(ApplicationError):
    """Se intentó registrar un email ya existente (HU-11)."""


class InvalidCredentialsError(ApplicationError):
    """Credenciales inválidas al iniciar sesión (HU-12)."""
