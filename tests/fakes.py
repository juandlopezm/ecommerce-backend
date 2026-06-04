"""Repositorios falsos en memoria para pruebas unitarias (sin base de datos).

Permiten probar los servicios en aislamiento gracias a las interfaces de repositorio (DI).
"""

from datetime import UTC, datetime

from app.application.errors import OrderNotFoundError, OutOfStockError, ProductNotFoundError
from app.domain.entities.order import Order, OrderStatus
from app.domain.entities.product import Product
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.product_repository import ProductRepository


class FakeProductRepository(ProductRepository):
    def __init__(self) -> None:
        self._items: dict[int, Product] = {}
        self._seq = 0

    def list(self, category: str | None = None, brand: str | None = None) -> list[Product]:
        items = list(self._items.values())
        if category:
            items = [p for p in items if p.category == category]
        if brand:
            items = [p for p in items if p.brand == brand]
        return items

    def get_by_id(self, product_id: int) -> Product | None:
        return self._items.get(product_id)

    def add(self, product: Product) -> Product:
        self._seq += 1
        product.id = self._seq
        self._items[product.id] = product
        return product

    def update(self, product: Product) -> Product:
        if product.id is not None:
            self._items[product.id] = product
        return product

    def delete(self, product_id: int) -> None:
        self._items.pop(product_id, None)


class FakeOrderRepository(OrderRepository):
    def __init__(self, products: FakeProductRepository) -> None:
        self._products = products
        self._orders: dict[int, Order] = {}
        self._seq = 0

    def create_checkout(self, order: Order) -> Order:
        for item in order.items:
            product = self._products.get_by_id(item.product_id)
            if product is None:
                raise ProductNotFoundError(item.product_id)
            if product.stock < item.quantity:
                raise OutOfStockError(item.product_id)
        for item in order.items:
            product = self._products.get_by_id(item.product_id)
            assert product is not None
            product.stock -= item.quantity
        self._seq += 1
        order.id = self._seq
        order.created_at = datetime.now(UTC)
        self._orders[order.id] = order
        return order

    def get_by_id(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    def list(self) -> list[Order]:
        return list(self._orders.values())

    def set_status(self, order_id: int, status: OrderStatus) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        order.status = status
        return order

    def cancel_and_restore_stock(self, order_id: int) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        if order.status != OrderStatus.CANCELADO:
            for item in order.items:
                product = self._products.get_by_id(item.product_id)
                if product is not None:
                    product.stock += item.quantity
            order.status = OrderStatus.CANCELADO
        return order
