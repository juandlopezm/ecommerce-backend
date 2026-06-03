"""Schemas Pydantic para productos (validación y serialización)."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """Datos para crear un producto (RF-08.2)."""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    brand: str = Field(default="", max_length=120)
    category: str = Field(default="", max_length=120)
    image_url: str = Field(default="", max_length=500)
    is_active: bool = True


class ProductUpdate(BaseModel):
    """Datos para actualizar un producto. Todos los campos son opcionales (PATCH parcial)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    brand: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=120)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProductRead(BaseModel):
    """Representación pública de un producto."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: Decimal
    stock: int
    brand: str
    category: str
    image_url: str
    is_active: bool
    is_available: bool
