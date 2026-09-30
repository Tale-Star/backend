"""Rutas de disponibilidad de la API."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])
versioned_router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Confirma que el proceso HTTP está disponible."""
    return {"status": "ok"}


@versioned_router.get("/health")
def versioned_health() -> dict[str, str]:
    """Confirma la disponibilidad de la API versionada."""
    return {"status": "ok"}

