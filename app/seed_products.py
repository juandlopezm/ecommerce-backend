"""Siembra 5 productos de prueba en el catálogo.

Uso:  python -m app.seed_products

Idempotente: omite los productos cuyo nombre ya exista. Útil para poblar el catálogo en
desarrollo (RF-01) y probar el frontend.
"""

from decimal import Decimal

from app.application.schemas.product import ProductCreate
from app.application.services.product_service import ProductService
from app.core.database import Base, SessionLocal, engine

# Importa el modelo para registrarlo en la metadata antes de create_all.
from app.infrastructure.models.product_model import ProductModel  # noqa: F401
from app.infrastructure.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)

SAMPLE_PRODUCTS: list[dict] = [
    {
        "name": "Sérum Facial Hidratante Ácido Hialurónico",
        "description": "Sérum ligero que hidrata en profundidad y suaviza la piel.",
        "price": Decimal("52000.00"),
        "stock": 30,
        "brand": "The Ordinary",
        "category": "Cuidado de la piel",
        "image_url": "https://picsum.photos/seed/serum/400/400",
    },
    {
        "name": "Base de Maquillaje Fit Me Matte",
        "description": "Base de cobertura media con acabado mate natural.",
        "price": Decimal("45000.00"),
        "stock": 25,
        "brand": "Maybelline",
        "category": "Maquillaje",
        "image_url": "https://picsum.photos/seed/base/400/400",
    },
    {
        "name": "Labial Líquido Mate Tono Nude Rose",
        "description": "Labial de larga duración con acabado mate aterciopelado.",
        "price": Decimal("38000.00"),
        "stock": 0,
        "brand": "NYX",
        "category": "Maquillaje",
        "image_url": "https://picsum.photos/seed/labial/400/400",
    },
    {
        "name": "Perfume Floral Eau de Parfum 50ml",
        "description": "Fragancia floral fresca para uso diario.",
        "price": Decimal("120000.00"),
        "stock": 12,
        "brand": "Miss Bloom",
        "category": "Perfumes",
        "image_url": "https://picsum.photos/seed/perfume/400/400",
    },
    {
        "name": "Crema Hidratante Facial",
        "description": "Crema humectante para piel normal a seca, uso diario.",
        "price": Decimal("60000.00"),
        "stock": 18,
        "brand": "CeraVe",
        "category": "Cuidado de la piel",
        "image_url": "https://picsum.photos/seed/crema/400/400",
    },
]


def seed_products() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        repo = SqlAlchemyProductRepository(session)
        existing = {p.name for p in repo.list()}
        service = ProductService(repo)
        created = 0
        for data in SAMPLE_PRODUCTS:
            if data["name"] in existing:
                continue
            service.create(ProductCreate(**data))
            created += 1
        skipped = len(SAMPLE_PRODUCTS) - created
        print(f"Productos creados: {created} (omitidos {skipped} ya existentes).")
    finally:
        session.close()


if __name__ == "__main__":
    seed_products()
