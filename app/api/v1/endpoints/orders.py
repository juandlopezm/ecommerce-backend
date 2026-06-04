"""Endpoints de compra y consulta de pedidos (RF-04 / RF-06)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_optional_user, get_order_service
from app.application.errors import (
    OrderNotFoundError,
    OutOfStockError,
    PaymentRejectedError,
    ProductNotFoundError,
)
from app.application.schemas.order import CheckoutRequest, OrderRead
from app.application.services.order_service import OrderService
from app.domain.entities.user import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(
    data: CheckoutRequest,
    service: OrderService = Depends(get_order_service),
    current_user: User | None = Depends(get_optional_user),
) -> OrderRead:
    """Procesa la compra (invitado o autenticado) y genera el pedido (RF-04 / HU-06/07)."""
    user_id = current_user.id if current_user else None
    try:
        order = service.checkout(data, user_id=user_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
        ) from exc
    except OutOfStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock insuficiente para uno o más productos",
        ) from exc
    except PaymentRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="El pago fue rechazado",
        ) from exc
    return OrderRead.model_validate(order)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    """Consulta un pedido por su id (confirmación / seguimiento, RF-04.6)."""
    try:
        order = service.get(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
        ) from exc
    return OrderRead.model_validate(order)
