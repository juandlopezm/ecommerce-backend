"""Entidades de dominio para pedidos (RF-06) y sus estados/pagos."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class OrderStatus(StrEnum):
    """Estados del pedido (RF-06.2)."""

    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    ENVIADO = "enviado"
    CANCELADO = "cancelado"


class PaymentMethod(StrEnum):
    """Métodos de pago soportados (RF-04.3 / RF-05)."""

    PASARELA = "pasarela"
    CONTRA_ENTREGA = "contra_entrega"


class PaymentStatus(StrEnum):
    """Estado del pago de un pedido (RF-05.3)."""

    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    PENDIENTE = "pendiente"


@dataclass
class OrderItem:
    """Línea de un pedido (snapshot del producto al momento de la compra)."""

    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


@dataclass
class Order:
    """Pedido con sus líneas, datos de envío, pago y estado (RF-06.1)."""

    customer_name: str
    customer_email: str
    customer_phone: str
    shipping_address: str
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    total: Decimal
    items: list[OrderItem] = field(default_factory=list)
    user_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
