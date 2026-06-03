"""Interfaz (puerto) del repositorio de productos — patrón Repository."""

from abc import ABC, abstractmethod

from app.domain.entities.product import Product


class ProductRepository(ABC):
    """Contrato de persistencia de productos."""

    @abstractmethod
    def list(self, category: str | None = None, brand: str | None = None) -> list[Product]:
        """Lista productos, opcionalmente filtrando por categoría y/o marca (RF-01.3)."""

    @abstractmethod
    def get_by_id(self, product_id: int) -> Product | None:
        """Devuelve el producto con ese id, o ``None`` si no existe."""

    @abstractmethod
    def add(self, product: Product) -> Product:
        """Persiste un producto nuevo y lo devuelve con su ``id``."""

    @abstractmethod
    def update(self, product: Product) -> Product:
        """Actualiza un producto existente y lo devuelve."""

    @abstractmethod
    def delete(self, product_id: int) -> None:
        """Elimina el producto con ese id."""
