"""Schemas Pydantic para pedidos y checkout (RF-04 / RF-06)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities.order import OrderStatus, PaymentMethod, PaymentStatus


class CheckoutItem(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class CheckoutRequest(BaseModel):
    """Datos del proceso de compra (RF-04.1/04.3)."""

    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: EmailStr
    customer_phone: str = Field(default="", max_length=50)
    shipping_address: str = Field(min_length=1, max_length=1000)
    payment_method: PaymentMethod
    items: list[CheckoutItem] = Field(min_length=1)
    # Permite simular un pago rechazado en la pasarela (sandbox, HU-07).
    simulate_payment_failure: bool = False


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    shipping_address: str
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    total: Decimal
    items: list[OrderItemRead]
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    """Cambio de estado de un pedido por el administrador (RF-08.7)."""

    status: OrderStatus
