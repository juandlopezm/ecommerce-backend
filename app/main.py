"""Punto de entrada de la API FastAPI (app factory)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.limiter import limiter


def _rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """Respuesta 429 cuando se supera el límite de peticiones (RNF-02.7)."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiados intentos. Inténtalo más tarde."},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="E-commerce API",
        description="API REST del e-commerce de productos de belleza (MVP).",
        version="0.1.0",
    )

    # Rate limiting (slowapi): patrón decorador + handler de excepción.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
