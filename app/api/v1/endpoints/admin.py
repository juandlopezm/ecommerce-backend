"""Endpoints del panel de administración (protegidos por rol). RF-08."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_order_service, get_product_service, require_admin
from app.application.errors import OrderNotFoundError
from app.application.schemas.order import OrderRead, OrderStatusUpdate
from app.application.schemas.product import ProductRead
from app.application.services.order_service import OrderService
from app.application.services.product_service import ProductService
from app.domain.entities.user import User

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/ping")
async def admin_ping(admin: User = Depends(require_admin)) -> dict[str, str]:
    """Ruta protegida de prueba: solo accesible para administradores (HU-13)."""
    return {"message": "pong", "admin": admin.email}


@router.get("/orders", response_model=list[OrderRead])
async def list_orders(service: OrderService = Depends(get_order_service)) -> list[OrderRead]:
    """Lista todos los pedidos con su detalle (RF-08.6 / HU-16)."""
    return [OrderRead.model_validate(o) for o in service.list()]


@router.patch("/orders/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    """Actualiza el estado de un pedido; al cancelar, restaura stock (RF-08.7 / RF-02.5)."""
    try:
        order = service.update_status(order_id, data.status)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
        ) from exc
    return OrderRead.model_validate(order)


@router.get("/products/low-stock", response_model=list[ProductRead])
async def low_stock_products(
    threshold: int = 5,
    service: ProductService = Depends(get_product_service),
) -> list[ProductRead]:
    """Productos con stock bajo o agotado (RF-08.8)."""
    return [ProductRead.model_validate(p) for p in service.list() if p.stock <= threshold]
