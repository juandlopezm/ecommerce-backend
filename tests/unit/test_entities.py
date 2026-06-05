"""Pruebas unitarias de la lógica de las entidades de dominio (caja blanca de propiedades)."""

from decimal import Decimal

from app.domain.entities.product import Product
from app.domain.entities.user import Role, User


def _product(stock: int, is_active: bool = True) -> Product:
    return Product(name="Labial", price=Decimal("10000"), stock=stock, is_active=is_active)


def test_product_available_when_active_and_in_stock() -> None:
    assert _product(stock=5).is_available is True


def test_product_not_available_when_out_of_stock() -> None:
    assert _product(stock=0).is_available is False


def test_product_not_available_when_inactive() -> None:
    assert _product(stock=5, is_active=False).is_available is False


def _user(role: Role) -> User:
    return User(email="a@x.com", hashed_password="h", full_name="A", role=role)


def test_user_is_admin_true_for_admin() -> None:
    assert _user(Role.ADMIN).is_admin is True


def test_user_is_admin_false_for_cliente() -> None:
    assert _user(Role.CLIENTE).is_admin is False


def test_product_available_with_stock_one_boundary() -> None:
    # Borde inferior de `stock > 0`: stock == 1 -> disponible.
    assert _product(stock=1).is_available is True


def test_product_not_available_with_negative_stock() -> None:
    # Edge: stock negativo (dato corrupto) -> no disponible.
    assert _product(stock=-1).is_available is False


def test_user_is_admin_false_for_invitado() -> None:
    # Tercer valor del enum Role: invitado tampoco es admin.
    assert _user(Role.INVITADO).is_admin is False
