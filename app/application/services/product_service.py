"""Servicio de productos: casos de uso del CRUD del catálogo (RF-01 / RF-08.2)."""

from app.application.errors import ProductNotFoundError
from app.application.schemas.product import ProductCreate, ProductUpdate
from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository


class ProductService:
    """Reglas de negocio del catálogo de productos."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def list(self, category: str | None = None, brand: str | None = None) -> list[Product]:
        return self._repository.list(category=category, brand=brand)

    def get(self, product_id: int) -> Product:
        product = self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    def create(self, data: ProductCreate) -> Product:
        product = Product(
            name=data.name,
            description=data.description,
            price=data.price,
            stock=data.stock,
            brand=data.brand,
            category=data.category,
            image_url=data.image_url,
            is_active=data.is_active,
        )
        return self._repository.add(product)

    def update(self, product_id: int, data: ProductUpdate) -> Product:
        product = self.get(product_id)
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(product, field, value)
        return self._repository.update(product)

    def delete(self, product_id: int) -> None:
        self.get(product_id)  # valida existencia (404 si no existe)
        self._repository.delete(product_id)
