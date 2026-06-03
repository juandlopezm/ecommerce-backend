"""Endpoints CRUD del catálogo de productos.

Lectura pública (RF-01); escritura restringida a administradores (RF-08.2 / HU-14).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_product_service, require_admin
from app.application.errors import ProductNotFoundError
from app.application.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.application.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])

_not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")


@router.get("", response_model=list[ProductRead])
async def list_products(
    category: str | None = None,
    brand: str | None = None,
    service: ProductService = Depends(get_product_service),
) -> list[ProductRead]:
    """Lista productos del catálogo, con filtros opcionales por categoría y marca (RF-01.1/01.3)."""
    products = service.list(category=category, brand=brand)
    return [ProductRead.model_validate(p) for p in products]


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """Devuelve el detalle de un producto (RF-01.2)."""
    try:
        product = service.get(product_id)
    except ProductNotFoundError as exc:
        raise _not_found from exc
    return ProductRead.model_validate(product)


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """Crea un producto (solo administrador, RF-08.2 / HU-14)."""
    product = service.create(data)
    return ProductRead.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductRead,
    dependencies=[Depends(require_admin)],
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """Actualiza un producto (solo administrador, RF-08.2 / HU-14)."""
    try:
        product = service.update(product_id, data)
    except ProductNotFoundError as exc:
        raise _not_found from exc
    return ProductRead.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
) -> None:
    """Elimina un producto (solo administrador, RF-08.2 / HU-14)."""
    try:
        service.delete(product_id)
    except ProductNotFoundError as exc:
        raise _not_found from exc
