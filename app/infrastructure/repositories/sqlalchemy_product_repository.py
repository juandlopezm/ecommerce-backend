"""Implementación del ``ProductRepository`` sobre SQLAlchemy."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.models.product_model import ProductModel


def _to_entity(model: ProductModel) -> Product:
    return Product(
        id=model.id,
        name=model.name,
        description=model.description,
        price=model.price,
        stock=model.stock,
        brand=model.brand,
        category=model.category,
        image_url=model.image_url,
        is_active=model.is_active,
    )


def _apply(model: ProductModel, product: Product) -> None:
    model.name = product.name
    model.description = product.description
    model.price = product.price
    model.stock = product.stock
    model.brand = product.brand
    model.category = product.category
    model.image_url = product.image_url
    model.is_active = product.is_active


class SqlAlchemyProductRepository(ProductRepository):
    """Repositorio de productos respaldado por una sesión SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, category: str | None = None, brand: str | None = None) -> list[Product]:
        stmt = select(ProductModel)
        if category:
            stmt = stmt.where(ProductModel.category == category)
        if brand:
            stmt = stmt.where(ProductModel.brand == brand)
        stmt = stmt.order_by(ProductModel.id)
        return [_to_entity(m) for m in self._session.scalars(stmt).all()]

    def get_by_id(self, product_id: int) -> Product | None:
        model = self._session.get(ProductModel, product_id)
        return _to_entity(model) if model else None

    def add(self, product: Product) -> Product:
        model = ProductModel()
        _apply(model, product)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def update(self, product: Product) -> Product:
        model = self._session.get(ProductModel, product.id)
        if model is None:
            raise ValueError(f"Producto {product.id} no encontrado")
        _apply(model, product)
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def delete(self, product_id: int) -> None:
        model = self._session.get(ProductModel, product_id)
        if model is not None:
            self._session.delete(model)
            self._session.commit()
