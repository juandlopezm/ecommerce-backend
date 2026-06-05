"""Pruebas unitarias de los handlers de los endpoints, llamándolos directamente (sin HTTP).

El foco es la lógica del controlador y la traducción de errores de negocio a códigos HTTP
(404 no encontrado, 409 conflicto/sin stock, 402 pago rechazado). Se usan repos reales sobre
SQLite en memoria y se ejecutan las corutinas con asyncio.run.
"""

import asyncio
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.endpoints import admin, auth, orders, products
from app.application.schemas.order import CheckoutItem, CheckoutRequest, OrderStatusUpdate
from app.application.schemas.product import ProductCreate, ProductUpdate
from app.application.schemas.user import UserCreate
from app.application.services.auth_service import AuthService
from app.application.services.order_service import OrderService
from app.application.services.product_service import ProductService
from app.domain.entities.order import OrderStatus, PaymentMethod
from app.domain.entities.user import Role, User
from app.infrastructure.repositories.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from app.infrastructure.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)
from app.infrastructure.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def _auth(db: Session) -> AuthService:
    return AuthService(SqlAlchemyUserRepository(db))


def _products(db: Session) -> ProductService:
    return ProductService(SqlAlchemyProductRepository(db))


def _orders(db: Session) -> OrderService:
    return OrderService(SqlAlchemyOrderRepository(db), SqlAlchemyProductRepository(db))


def _crear_producto(db: Session) -> Any:
    return _products(db).create(
        ProductCreate(
            name="Labial",
            description="",
            price=Decimal("10000"),
            stock=5,
            brand="NYX",
            category="Maquillaje",
            image_url="",
            is_active=True,
        )
    )


def _checkout_req(product_id: int, quantity: int = 2, **overrides: Any) -> CheckoutRequest:
    data: dict = {
        "customer_name": "Ana",
        "customer_email": "ana@x.com",
        "customer_phone": "3",
        "shipping_address": "Calle 1",
        "payment_method": PaymentMethod.PASARELA,
        "items": [CheckoutItem(product_id=product_id, quantity=quantity)],
    }
    data.update(overrides)
    return CheckoutRequest(**data)


# --- auth ---------------------------------------------------------------------------------


# register crea el usuario; registrar el mismo correo de nuevo devuelve 409.
def test_register_endpoint(db_session: Session) -> None:
    data = UserCreate(email="a@x.com", password="Secreta123!", full_name="A")
    user = run(auth.register(data, _auth(db_session)))
    assert user.email == "a@x.com"
    with pytest.raises(HTTPException) as exc:
        run(auth.register(data, _auth(db_session)))
    assert exc.value.status_code == 409


# me devuelve los datos del usuario autenticado.
def test_me_endpoint() -> None:
    user = User(id=1, email="a@x.com", hashed_password="h", full_name="A", role=Role.CLIENTE)
    result = run(auth.me(current_user=user))
    assert result.email == "a@x.com"


# --- products -----------------------------------------------------------------------------


# get_product devuelve el producto; si no existe, lanza 404.
def test_get_product_endpoint(db_session: Session) -> None:
    product = _crear_producto(db_session)
    result = run(products.get_product(product.id, _products(db_session)))
    assert result.id == product.id
    with pytest.raises(HTTPException) as exc:
        run(products.get_product(9999, _products(db_session)))
    assert exc.value.status_code == 404


# create + list + update + delete del catálogo (camino feliz).
def test_crud_products_endpoint(db_session: Session) -> None:
    created = run(
        products.create_product(
            ProductCreate(
                name="X",
                description="",
                price=Decimal("1"),
                stock=1,
                brand="",
                category="",
                image_url="",
                is_active=True,
            ),
            _products(db_session),
        )
    )
    assert created.id is not None
    assert len(run(products.list_products(None, None, _products(db_session)))) == 1
    updated = run(
        products.update_product(created.id, ProductUpdate(stock=0), _products(db_session))
    )
    assert updated.stock == 0
    run(products.delete_product(created.id, _products(db_session)))
    with pytest.raises(HTTPException):
        run(products.get_product(created.id, _products(db_session)))


# update y delete de un producto inexistente devuelven 404.
def test_products_not_found(db_session: Session) -> None:
    with pytest.raises(HTTPException) as e1:
        run(products.update_product(9999, ProductUpdate(stock=1), _products(db_session)))
    assert e1.value.status_code == 404
    with pytest.raises(HTTPException) as e2:
        run(products.delete_product(9999, _products(db_session)))
    assert e2.value.status_code == 404


# --- orders -------------------------------------------------------------------------------


# checkout como invitado genera el pedido confirmado.
def test_checkout_endpoint(db_session: Session) -> None:
    product = _crear_producto(db_session)
    result = run(orders.checkout(_checkout_req(product.id), _orders(db_session), None))
    assert result.status == OrderStatus.CONFIRMADO


# checkout: producto inexistente -> 404, sin stock -> 409, pago rechazado -> 402.
def test_checkout_errores(db_session: Session) -> None:
    product = _crear_producto(db_session)
    with pytest.raises(HTTPException) as e1:
        run(orders.checkout(_checkout_req(9999), _orders(db_session), None))
    assert e1.value.status_code == 404
    with pytest.raises(HTTPException) as e2:
        run(orders.checkout(_checkout_req(product.id, quantity=999), _orders(db_session), None))
    assert e2.value.status_code == 409
    with pytest.raises(HTTPException) as e3:
        run(
            orders.checkout(
                _checkout_req(product.id, simulate_payment_failure=True),
                _orders(db_session),
                None,
            )
        )
    assert e3.value.status_code == 402


# get_order devuelve el pedido; con un id inexistente, 404.
def test_get_order_endpoint(db_session: Session) -> None:
    product = _crear_producto(db_session)
    created = run(orders.checkout(_checkout_req(product.id), _orders(db_session), None))
    got = run(orders.get_order(created.id, _orders(db_session)))
    assert got.id == created.id
    with pytest.raises(HTTPException) as exc:
        run(orders.get_order(9999, _orders(db_session)))
    assert exc.value.status_code == 404


# --- admin --------------------------------------------------------------------------------


# admin_ping responde pong; list_orders lista; cambiar estado funciona y 404 si no existe;
# low_stock devuelve una lista.
def test_admin_endpoints(db_session: Session) -> None:
    admin_user = User(id=1, email="a@x.com", hashed_password="h", full_name="A", role=Role.ADMIN)
    assert run(admin.admin_ping(admin_user))["message"] == "pong"

    product = _crear_producto(db_session)
    created = run(orders.checkout(_checkout_req(product.id), _orders(db_session), None))
    assert len(run(admin.list_orders(_orders(db_session)))) == 1

    cambiado = run(
        admin.update_order_status(
            created.id, OrderStatusUpdate(status=OrderStatus.ENVIADO), _orders(db_session)
        )
    )
    assert cambiado.status == OrderStatus.ENVIADO

    with pytest.raises(HTTPException) as exc:
        run(
            admin.update_order_status(
                9999, OrderStatusUpdate(status=OrderStatus.ENVIADO), _orders(db_session)
            )
        )
    assert exc.value.status_code == 404

    assert isinstance(run(admin.low_stock_products(5, _products(db_session))), list)
