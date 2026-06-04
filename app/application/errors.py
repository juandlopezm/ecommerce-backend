"""Excepciones de la capa de aplicación (independientes de HTTP)."""


class ApplicationError(Exception):
    """Base de los errores de negocio."""


class EmailAlreadyExistsError(ApplicationError):
    """Se intentó registrar un email ya existente (HU-11)."""


class InvalidCredentialsError(ApplicationError):
    """Credenciales inválidas al iniciar sesión (HU-12)."""


class ProductNotFoundError(ApplicationError):
    """No se encontró el producto solicitado."""


class OutOfStockError(ApplicationError):
    """No hay stock suficiente para completar la compra (RF-02.3 / HU-10)."""


class PaymentRejectedError(ApplicationError):
    """El pago fue rechazado por la pasarela (HU-07)."""


class OrderNotFoundError(ApplicationError):
    """No se encontró el pedido solicitado."""
