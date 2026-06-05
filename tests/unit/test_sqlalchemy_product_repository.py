"""Pruebas unitarias del repositorio de productos sobre SQLAlchemy (SQLite en memoria)."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.domain.entities.product import Product
from app.infrastructure.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)


def _product(name: str = "Labial", category: str = "Maquillaje", brand: str = "NYX") -> Product:
    return Product(name=name, price=Decimal("10000"), stock=5, category=category, brand=brand)


# add() persiste el producto y get_by_id() lo recupera mapeado a entidad.
def test_add_y_get_by_id(db_session: Session) -> None:
    repo = SqlAlchemyProductRepository(db_session)
    created = repo.add(_product())
    assert created.id is not None
    found = repo.get_by_id(created.id)
    assert found is not None
    assert found.name == "Labial"
    assert repo.get_by_id(9999) is None


# list() debe filtrar por categoría y por marca.
def test_list_filtra(db_session: Session) -> None:
    repo = SqlAlchemyProductRepository(db_session)
    repo.add(_product(category="Maquillaje", brand="NYX"))
    repo.add(_product(name="Perfume", category="Perfumes", brand="Bloom"))
    assert len(repo.list()) == 2
    assert len(repo.list(category="Maquillaje")) == 1
    assert len(repo.list(brand="Bloom")) == 1


# update() modifica un producto existente y conserva su id.
def test_update_modifica(db_session: Session) -> None:
    repo = SqlAlchemyProductRepository(db_session)
    created = repo.add(_product())
    created.stock = 0
    created.name = "Labial mate"
    updated = repo.update(created)
    assert updated.stock == 0
    assert updated.name == "Labial mate"


# update() sobre un producto inexistente debe lanzar ValueError.
def test_update_inexistente_lanza(db_session: Session) -> None:
    repo = SqlAlchemyProductRepository(db_session)
    fantasma = _product()
    fantasma.id = 9999
    with pytest.raises(ValueError):
        repo.update(fantasma)


# delete() elimina el producto; luego get_by_id() devuelve None.
def test_delete(db_session: Session) -> None:
    repo = SqlAlchemyProductRepository(db_session)
    created = repo.add(_product())
    assert created.id is not None
    repo.delete(created.id)
    assert repo.get_by_id(created.id) is None


# delete() de un id inexistente no debe lanzar error (operación idempotente).
def test_delete_inexistente_no_lanza(db_session: Session) -> None:
    repo = SqlAlchemyProductRepository(db_session)
    repo.delete(9999)  # no debe levantar excepción
