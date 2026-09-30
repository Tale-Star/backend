"""Modelo SQLAlchemy de infraestructura para GenerationJob."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class GenerationJobRecord(Base):
    """Fila persistida del agregado GenerativeMedia."""

    __tablename__ = "generation_jobs"
    __table_args__ = (
        CheckConstraint("type IN ('Image', 'Music')", name="generation_job_type"),
        CheckConstraint(
            "status IN ('Pending', 'Processing', 'Succeeded', 'Failed')",
            name="generation_job_status",
        ),
        CheckConstraint("attempts >= 0", name="generation_job_attempts"),
        Index("ix_generation_jobs_status_created_at", "status", "created_at"),
        Index("ix_generation_jobs_owner_id", "owner_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("identity_users.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
