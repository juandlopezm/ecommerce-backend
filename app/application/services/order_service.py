"""Servicio de pedidos: checkout, consulta y gestión de estado (RF-04 / RF-06)."""

from decimal import Decimal

from app.application.errors import OrderNotFoundError, PaymentRejectedError, ProductNotFoundError
from app.application.schemas.order import CheckoutRequest
from app.application.services.payment import get_payment_strategy
from app.domain.entities.order import (
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
)
from app.domain.repositories.order_repository import OrderRepository
from app.domain.repositories.product_repository import ProductRepository


class OrderService:
    """Reglas de negocio del proceso de compra y los pedidos."""

    def __init__(self, orders: OrderRepository, products: ProductRepository) -> None:
        self._orders = orders
        self._products = products

    def checkout(self, data: CheckoutRequest, user_id: int | None = None) -> Order:
        """Procesa la compra: arma el pedido, cobra (simulado) y descuenta stock (RF-04)."""
        items: list[OrderItem] = []
        total = Decimal("0")
        for line in data.items:
            product = self._products.get_by_id(line.product_id)
            if product is None:
                raise ProductNotFoundError(line.product_id)
            subtotal = product.price * line.quantity
            total += subtotal
            items.append(
                OrderItem(
                    product_id=line.product_id,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=line.quantity,
                    subtotal=subtotal,
                )
            )

        # Pago simulado (Strategy/Factory).
        strategy = get_payment_strategy(data.payment_method)
        payment_status = strategy.process(total, data.simulate_payment_failure)
        if payment_status == PaymentStatus.RECHAZADO:
            raise PaymentRejectedError()

        status = (
            OrderStatus.CONFIRMADO
            if payment_status == PaymentStatus.APROBADO
            else OrderStatus.PENDIENTE
        )

        order = Order(
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            shipping_address=data.shipping_address,
            payment_method=data.payment_method,
            payment_status=payment_status,
            status=status,
            total=total,
            items=items,
            user_id=user_id,
        )
        # Descuenta el stock de forma atómica; lanza OutOfStockError si no alcanza.
        return self._orders.create_checkout(order)

    def get(self, order_id: int) -> Order:
        order = self._orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    def list(self) -> list[Order]:
        return self._orders.list()

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        """Actualiza el estado; si se cancela, restaura el stock (RF-02.5 / RF-08.7)."""
        if status == OrderStatus.CANCELADO:
            return self._orders.cancel_and_restore_stock(order_id)
        return self._orders.set_status(order_id, status)
