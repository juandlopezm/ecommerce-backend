"""Pruebas unitarias de OrderService (checkout, pagos y estados) con repos falsos.

Cubre las ramas del checkout: aprobado/pendiente/rechazado, sin stock y producto inexistente,
además del cambio de estado y la restauración de stock al cancelar.
"""

from decimal import Decimal

import pytest

from app.application.errors import (
    OrderNotFoundError,
    OutOfStockError,
    PaymentRejectedError,
    ProductNotFoundError,
)
from app.application.schemas.order import CheckoutItem, CheckoutRequest
from app.application.services.order_service import OrderService
from app.domain.entities.order import OrderStatus, PaymentMethod, PaymentStatus
from app.domain.entities.product import Product
from tests.fakes import FakeOrderRepository, FakeProductRepository


@pytest.fixture
def products() -> FakeProductRepository:
    repo = FakeProductRepository()
    repo.add(Product(name="Labial", price=Decimal("10000"), stock=5, category="Maquillaje"))
    return repo


@pytest.fixture
def service(products: FakeProductRepository) -> OrderService:
    return OrderService(FakeOrderRepository(products), products)


def _request(**overrides: object) -> CheckoutRequest:
    data: dict = {
        "customer_name": "Ana",
        "customer_email": "ana@x.com",
        "customer_phone": "3",
        "shipping_address": "Calle 1",
        "payment_method": PaymentMethod.PASARELA,
        "items": [CheckoutItem(product_id=1, quantity=2)],
    }
    data.update(overrides)
    return CheckoutRequest(**data)


def test_checkout_gateway_confirms_and_decrements_stock(
    service: OrderService, products: FakeProductRepository
) -> None:
    order = service.checkout(_request())
    assert order.status == OrderStatus.CONFIRMADO
    assert order.payment_status == PaymentStatus.APROBADO
    assert order.total == Decimal("20000")
    assert products.get_by_id(1).stock == 3  # type: ignore[union-attr]


def test_checkout_contra_entrega_is_pending(service: OrderService) -> None:
    order = service.checkout(_request(payment_method=PaymentMethod.CONTRA_ENTREGA))
    assert order.status == OrderStatus.PENDIENTE
    assert order.payment_status == PaymentStatus.PENDIENTE


def test_checkout_rejected_payment_raises_and_keeps_stock(
    service: OrderService, products: FakeProductRepository
) -> None:
    with pytest.raises(PaymentRejectedError):
        service.checkout(_request(simulate_payment_failure=True))
    assert products.get_by_id(1).stock == 5  # type: ignore[union-attr]


def test_checkout_out_of_stock_raises_and_keeps_stock(
    service: OrderService, products: FakeProductRepository
) -> None:
    with pytest.raises(OutOfStockError):
        service.checkout(_request(items=[CheckoutItem(product_id=1, quantity=99)]))
    assert products.get_by_id(1).stock == 5  # type: ignore[union-attr]


def test_checkout_unknown_product_raises(service: OrderService) -> None:
    with pytest.raises(ProductNotFoundError):
        service.checkout(_request(items=[CheckoutItem(product_id=999, quantity=1)]))


def test_update_status_to_enviado(service: OrderService) -> None:
    order = service.checkout(_request())
    updated = service.update_status(order.id, OrderStatus.ENVIADO)  # type: ignore[arg-type]
    assert updated.status == OrderStatus.ENVIADO


def test_cancel_restores_stock(service: OrderService, products: FakeProductRepository) -> None:
    order = service.checkout(_request())  # 5 -> 3
    service.update_status(order.id, OrderStatus.CANCELADO)  # type: ignore[arg-type]
    assert products.get_by_id(1).stock == 5  # type: ignore[union-attr]


def test_get_missing_order_raises(service: OrderService) -> None:
    with pytest.raises(OrderNotFoundError):
        service.get(999)


def test_checkout_sums_total_of_multiple_items(products: FakeProductRepository) -> None:
    # El bucle del checkout recorre varios ítems y suma sus subtotales.
    products.add(Product(name="Base", price=Decimal("5000"), stock=10))  # id = 2
    service = OrderService(FakeOrderRepository(products), products)
    order = service.checkout(
        _request(
            items=[
                CheckoutItem(product_id=1, quantity=2),
                CheckoutItem(product_id=2, quantity=3),
            ]
        )
    )
    assert order.total == Decimal("35000")  # 2*10000 + 3*5000
    assert len(order.items) == 2
    assert products.get_by_id(1).stock == 3  # type: ignore[union-attr]
    assert products.get_by_id(2).stock == 7  # type: ignore[union-attr]


def test_list_returns_all_orders(service: OrderService) -> None:
    # service.list() devuelve todos los pedidos creados.
    service.checkout(_request())
    service.checkout(_request())
    assert len(service.list()) == 2
