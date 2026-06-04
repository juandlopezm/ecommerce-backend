"""Pruebas de integración de los endpoints de productos (RF-01 / RF-08.2 / HU-14)."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.domain.entities.product import Product

PRODUCTS_URL = "/api/v1/products"
NEW_PRODUCT = {
    "name": "Labial",
    "price": "10000.00",
    "stock": 5,
    "brand": "NYX",
    "category": "Maquillaje",
}


def test_list_empty(client: TestClient) -> None:
    assert client.get(PRODUCTS_URL).json() == []


def test_create_requires_authentication(client: TestClient) -> None:
    resp = client.post(PRODUCTS_URL, json=NEW_PRODUCT)
    assert resp.status_code == 401


def test_create_as_admin(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.post(PRODUCTS_URL, headers=admin_headers, json=NEW_PRODUCT)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Labial"
    assert body["is_available"] is True


def test_create_forbidden_for_client(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "c@x.com", "password": "Secreta123!", "full_name": "C"},
    )
    token = client.post(
        "/api/v1/auth/login", data={"username": "c@x.com", "password": "Secreta123!"}
    ).json()["access_token"]
    resp = client.post(PRODUCTS_URL, headers={"Authorization": f"Bearer {token}"}, json=NEW_PRODUCT)
    assert resp.status_code == 403


def test_get_and_not_found(client: TestClient, make_product: Callable[..., Product]) -> None:
    product = make_product()
    assert client.get(f"{PRODUCTS_URL}/{product.id}").status_code == 200
    assert client.get(f"{PRODUCTS_URL}/999").status_code == 404


def test_update_and_delete(
    client: TestClient, admin_headers: dict[str, str], make_product: Callable[..., Product]
) -> None:
    product = make_product()
    updated = client.put(f"{PRODUCTS_URL}/{product.id}", headers=admin_headers, json={"stock": 0})
    assert updated.status_code == 200
    assert updated.json()["is_available"] is False

    assert client.delete(f"{PRODUCTS_URL}/{product.id}", headers=admin_headers).status_code == 204
    assert client.get(f"{PRODUCTS_URL}/{product.id}").status_code == 404


def test_filter_by_category(client: TestClient, make_product: Callable[..., Product]) -> None:
    make_product(category="Maquillaje")
    make_product(category="Perfumes")
    resp = client.get(PRODUCTS_URL, params={"category": "Maquillaje"})
    assert len(resp.json()) == 1
