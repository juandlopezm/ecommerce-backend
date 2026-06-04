"""Implementación del ``OrderRepository`` sobre SQLAlchemy (con checkout atómico)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.errors import OrderNotFoundError, OutOfStockError, ProductNotFoundError
from app.domain.entities.order import (
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.repositories.order_repository import OrderRepository
from app.infrastructure.models.order_model import OrderItemModel, OrderModel
from app.infrastructure.models.product_model import ProductModel


def _to_entity(model: OrderModel) -> Order:
    return Order(
        id=model.id,
        customer_name=model.customer_name,
        customer_email=model.customer_email,
        customer_phone=model.customer_phone,
        shipping_address=model.shipping_address,
        payment_method=PaymentMethod(model.payment_method),
        payment_status=PaymentStatus(model.payment_status),
        status=OrderStatus(model.status),
        total=model.total,
        user_id=model.user_id,
        created_at=model.created_at,
        items=[
            OrderItem(
                product_id=i.product_id,
                product_name=i.product_name,
                unit_price=i.unit_price,
                quantity=i.quantity,
                subtotal=i.subtotal,
            )
            for i in model.items
        ],
    )


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_checkout(self, order: Order) -> Order:
        session = self._session
        try:
            # Bloquea las filas de producto y valida/descuenta stock de forma atómica (HU-10).
            for item in order.items:
                product = session.get(ProductModel, item.product_id, with_for_update=True)
                if product is None:
                    raise ProductNotFoundError(item.product_id)
                if product.stock < item.quantity:
                    raise OutOfStockError(item.product_id)
                product.stock -= item.quantity

            model = OrderModel(
                customer_name=order.customer_name,
                customer_email=order.customer_email,
                customer_phone=order.customer_phone,
                shipping_address=order.shipping_address,
                payment_method=order.payment_method.value,
                payment_status=order.payment_status.value,
                status=order.status.value,
                total=order.total,
                user_id=order.user_id,
                items=[
                    OrderItemModel(
                        product_id=i.product_id,
                        product_name=i.product_name,
                        unit_price=i.unit_price,
                        quantity=i.quantity,
                        subtotal=i.subtotal,
                    )
                    for i in order.items
                ],
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return _to_entity(model)
        except Exception:
            session.rollback()
            raise

    def get_by_id(self, order_id: int) -> Order | None:
        model = self._session.get(OrderModel, order_id)
        return _to_entity(model) if model else None

    def list(self) -> list[Order]:
        stmt = select(OrderModel).order_by(OrderModel.id.desc())
        return [_to_entity(m) for m in self._session.scalars(stmt).all()]

    def set_status(self, order_id: int, status: OrderStatus) -> Order:
        model = self._session.get(OrderModel, order_id)
        if model is None:
            raise OrderNotFoundError(order_id)
        model.status = status.value
        self._session.commit()
        self._session.refresh(model)
        return _to_entity(model)

    def cancel_and_restore_stock(self, order_id: int) -> Order:
        session = self._session
        try:
            model = session.get(OrderModel, order_id)
            if model is None:
                raise OrderNotFoundError(order_id)
            if model.status != OrderStatus.CANCELADO.value:
                for item in model.items:
                    product = session.get(ProductModel, item.product_id, with_for_update=True)
                    if product is not None:
                        product.stock += item.quantity
                model.status = OrderStatus.CANCELADO.value
                session.commit()
                session.refresh(model)
            return _to_entity(model)
        except Exception:
            session.rollback()
            raise
