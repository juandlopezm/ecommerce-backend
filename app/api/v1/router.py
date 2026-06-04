"""Router agregado de la API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, orders, products

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
