"""Entidad de dominio Producto. Independiente de la capa de persistencia."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Product:
    """Producto del catálogo (RF-01 / RF-08.2)."""

    name: str
    price: Decimal
    stock: int
    description: str = ""
    brand: str = ""
    category: str = ""
    image_url: str = ""
    is_active: bool = True
    id: int | None = None

    @property
    def is_available(self) -> bool:
        """Disponible si está activo y tiene stock (RF-01.5 / RF-02.4)."""
        return self.is_active and self.stock > 0
