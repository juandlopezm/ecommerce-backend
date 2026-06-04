"""Pruebas de integración del checkout y la gestión de pedidos (RF-04/05/06 / HU-06..10/16)."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.domain.entities.product import Product

ORDERS_URL = "/api/v1/orders"
ADMIN_ORDERS_URL = "/api/v1/admin/orders"


def _payload(product_id: int, quantity: int = 2, **overrides: object) -> dict:
    data: dict = {
        "customer_name": "Ana",
        "customer_email": "ana@x.com",
        "customer_phone": "300",
        "shipping_address": "Calle 1",
        "payment_method": "pasarela",
        "items": [{"product_id": product_id, "quantity": quantity}],
    }
    data.update(overrides)
    return data


def _product_stock(client: TestClient, product_id: int) -> int:
    return client.get(f"/api/v1/products/{product_id}").json()["stock"]


def test_checkout_gateway_confirms_and_decrements_stock(
    client: TestClient, make_product: Callable[..., Product]
) -> None:
    product = make_product(stock=5)
    resp = client.post(ORDERS_URL, json=_payload(product.id))
    assert resp.status_code == 201
    assert resp.json()["status"] == "confirmado"
    assert _product_stock(client, product.id) == 3


def test_checkout_contra_entrega_is_pending(
    client: TestClient, make_product: Callable[..., Product]
) -> None:
    product = make_product(stock=5)
    resp = client.post(ORDERS_URL, json=_payload(product.id, payment_method="contra_entrega"))
    assert resp.status_code == 201
    assert resp.json()["status"] == "pendiente"


def test_checkout_rejected_payment_returns_402(
    client: TestClient, make_product: Callable[..., Product]
) -> None:
    product = make_product(stock=5)
    resp = client.post(ORDERS_URL, json=_payload(product.id, simulate_payment_failure=True))
    assert resp.status_code == 402


def test_checkout_out_of_stock_returns_409(
    client: TestClient, make_product: Callable[..., Product]
) -> None:
    product = make_product(stock=1)
    resp = client.post(ORDERS_URL, json=_payload(product.id, quantity=5))
    assert resp.status_code == 409


def test_get_order_and_not_found(client: TestClient, make_product: Callable[..., Product]) -> None:
    product = make_product(stock=5)
    order_id = client.post(ORDERS_URL, json=_payload(product.id)).json()["id"]
    assert client.get(f"{ORDERS_URL}/{order_id}").status_code == 200
    assert client.get(f"{ORDERS_URL}/999").status_code == 404


def test_admin_orders_requires_token(client: TestClient) -> None:
    assert client.get(ADMIN_ORDERS_URL).status_code == 401


def test_admin_list_and_cancel_restores_stock(
    client: TestClient, admin_headers: dict[str, str], make_product: Callable[..., Product]
) -> None:
    product = make_product(stock=5)
    order_id = client.post(ORDERS_URL, json=_payload(product.id)).json()["id"]  # 5 -> 3
    assert len(client.get(ADMIN_ORDERS_URL, headers=admin_headers).json()) == 1

    resp = client.patch(
        f"{ADMIN_ORDERS_URL}/{order_id}/status", headers=admin_headers, json={"status": "cancelado"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelado"
    assert _product_stock(client, product.id) == 5


def test_low_stock_endpoint(
    client: TestClient, admin_headers: dict[str, str], make_product: Callable[..., Product]
) -> None:
    make_product(stock=2)
    make_product(stock=50)
    resp = client.get("/api/v1/admin/products/low-stock", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
