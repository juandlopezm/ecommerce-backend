"""Endpoints del panel de administración (protegidos por rol). Base para RF-08."""

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.domain.entities.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
async def admin_ping(admin: User = Depends(require_admin)) -> dict[str, str]:
    """Ruta protegida de prueba: solo accesible para administradores (HU-13)."""
    return {"message": "pong", "admin": admin.email}
