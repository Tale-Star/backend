"""Entidad de identidad del adulto propietario de la cuenta Tale Star."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.shared.domain.entity import Entity


@dataclass(eq=False, slots=True)
class User(Entity):
    """Cuenta única de adulto, con credenciales almacenadas solo como hashes."""

    email: str
    display_name: str
    password_hash: str
    parental_pin_hash: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
