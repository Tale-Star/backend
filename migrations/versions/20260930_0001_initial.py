"""Inicializa el historial; cada contexto añadirá sus tablas con revisiones propias."""

from collections.abc import Sequence

revision: str = "20260930_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establece la revisión base sin imponer tablas de dominio prematuras."""
    return None


def downgrade() -> None:
    """Revierte la revisión base, que todavía no crea tablas propias."""
    return None

