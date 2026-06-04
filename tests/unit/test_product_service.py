"""Pruebas unitarias de ProductService usando un repositorio falso en memoria."""

from decimal import Decimal

import pytest

from app.application.errors import ProductNotFoundError
from app.application.schemas.product import ProductCreate, ProductUpdate
from app.application.services.product_service import ProductService
from tests.fakes import FakeProductRepository


@pytest.fixture
def service() -> ProductService:
    return ProductService(FakeProductRepository())


def _create(**overrides: object) -> ProductCreate:
    data: dict = {
        "name": "Labial",
        "description": "",
        "price": Decimal("10000"),
        "stock": 5,
        "brand": "NYX",
        "category": "Maquillaje",
        "image_url": "",
        "is_active": True,
    }
    data.update(overrides)
    return ProductCreate(**data)


def test_create_and_get(service: ProductService) -> None:
    created = service.create(_create())
    assert created.id is not None
    assert service.get(created.id).name == "Labial"


def test_get_missing_raises(service: ProductService) -> None:
    with pytest.raises(ProductNotFoundError):
        service.get(999)


def test_update_is_partial(service: ProductService) -> None:
    created = service.create(_create())
    updated = service.update(created.id, ProductUpdate(stock=0))
    assert updated.stock == 0
    assert updated.name == "Labial"  # los campos no enviados se conservan


def test_update_missing_raises(service: ProductService) -> None:
    with pytest.raises(ProductNotFoundError):
        service.update(999, ProductUpdate(stock=1))


def test_delete_removes_product(service: ProductService) -> None:
    created = service.create(_create())
    service.delete(created.id)
    with pytest.raises(ProductNotFoundError):
        service.get(created.id)


def test_delete_missing_raises(service: ProductService) -> None:
    with pytest.raises(ProductNotFoundError):
        service.delete(999)


def test_list_filters_by_category(service: ProductService) -> None:
    service.create(_create(category="Maquillaje"))
    service.create(_create(category="Perfumes"))
    assert len(service.list(category="Maquillaje")) == 1
    assert len(service.list()) == 2
