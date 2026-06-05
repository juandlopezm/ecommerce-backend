"""Pruebas unitarias del repositorio de pedidos sobre SQLAlchemy (SQLite en memoria).

Verifica el checkout atómico (descuento de stock), la consulta, el cambio de estado y la
restauración de stock al cancelar.
"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.application.errors import OrderNotFoundError, OutOfStockError, ProductNotFoundError
from app.domain.entities.order import (
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.entities.product import Product
from app.infrastructure.repositories.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from app.infrastructure.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)


@pytest.fixture
def product(db_session: Session) -> Product:
    # Producto con stock 5 para usar en los pedidos.
    return SqlAlchemyProductRepository(db_session).add(
        Product(name="Labial", price=Decimal("10000"), stock=5, category="Maquillaje")
    )


def _order(product_id: int, quantity: int = 2) -> Order:
    return Order(
        customer_name="Ana",
        customer_email="ana@x.com",
        customer_phone="3",
        shipping_address="Calle 1",
        payment_method=PaymentMethod.PASARELA,
        payment_status=PaymentStatus.APROBADO,
        status=OrderStatus.CONFIRMADO,
        total=Decimal("10000") * quantity,
        items=[
            OrderItem(
                product_id=product_id,
                product_name="Labial",
                unit_price=Decimal("10000"),
                quantity=quantity,
                subtotal=Decimal("10000") * quantity,
            )
        ],
    )


def _stock(db_session: Session, product_id: int) -> int:
    found = SqlAlchemyProductRepository(db_session).get_by_id(product_id)
    assert found is not None
    return found.stock


# create_checkout() persiste el pedido y descuenta el stock de forma atómica.
def test_create_checkout_descuenta_stock(db_session: Session, product: Product) -> None:
    orders = SqlAlchemyOrderRepository(db_session)
    assert product.id is not None
    order = orders.create_checkout(_order(product.id))
    assert order.id is not None
    assert _stock(db_session, product.id) == 3


# get_by_id() devuelve el pedido con sus líneas; list() lo incluye; id inexistente -> None.
def test_get_y_list(db_session: Session, product: Product) -> None:
    orders = SqlAlchemyOrderRepository(db_session)
    assert product.id is not None
    created = orders.create_checkout(_order(product.id))
    assert created.id is not None
    found = orders.get_by_id(created.id)
    assert found is not None
    assert len(found.items) == 1
    assert len(orders.list()) == 1
    assert orders.get_by_id(9999) is None


# Sin stock suficiente, create_checkout() lanza OutOfStockError y NO persiste ni descuenta.
def test_create_checkout_sin_stock(db_session: Session, product: Product) -> None:
    orders = SqlAlchemyOrderRepository(db_session)
    assert product.id is not None
    with pytest.raises(OutOfStockError):
        orders.create_checkout(_order(product.id, quantity=999))
    assert _stock(db_session, product.id) == 5
    assert orders.list() == []


# create_checkout() con un producto inexistente lanza ProductNotFoundError.
def test_create_checkout_producto_inexistente(db_session: Session) -> None:
    orders = SqlAlchemyOrderRepository(db_session)
    with pytest.raises(ProductNotFoundError):
        orders.create_checkout(_order(9999))


# set_status() cambia el estado; con un id inexistente lanza OrderNotFoundError.
def test_set_status(db_session: Session, product: Product) -> None:
    orders = SqlAlchemyOrderRepository(db_session)
    assert product.id is not None
    created = orders.create_checkout(_order(product.id))
    assert created.id is not None
    updated = orders.set_status(created.id, OrderStatus.ENVIADO)
    assert updated.status == OrderStatus.ENVIADO
    with pytest.raises(OrderNotFoundError):
        orders.set_status(9999, OrderStatus.ENVIADO)


# cancel_and_restore_stock() cancela y devuelve el stock; cancelar de nuevo no lo duplica.
def test_cancel_restaura_stock(db_session: Session, product: Product) -> None:
    orders = SqlAlchemyOrderRepository(db_session)
    assert product.id is not None
    created = orders.create_checkout(_order(product.id))  # 5 -> 3
    assert created.id is not None
    cancelled = orders.cancel_and_restore_stock(created.id)
    assert cancelled.status == OrderStatus.CANCELADO
    assert _stock(db_session, product.id) == 5
    # Cancelar otra vez no vuelve a sumar stock (rama "ya cancelado").
    orders.cancel_and_restore_stock(created.id)
    assert _stock(db_session, product.id) == 5
    with pytest.raises(OrderNotFoundError):
        orders.cancel_and_restore_stock(9999)
