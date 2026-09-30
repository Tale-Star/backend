"""Agregado GenerationJob y reglas de sus transiciones."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.shared.domain.entity import Entity


class GenerationType(StrEnum):
    IMAGE = "Image"
    MUSIC = "Music"


class GenerationStatus(StrEnum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


class InvalidGenerationJobTransition(ValueError):
    """La transición solicitada no está permitida desde el estado actual."""


@dataclass(eq=False, slots=True)
class GenerationJob(Entity):
    """Solicitud persistente de generación y resultado asociado."""

    type: GenerationType
    payload: dict[str, Any]
    owner_id: UUID | None = None
    seed: int | None = None
    status: GenerationStatus = GenerationStatus.PENDING
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0

    def mark_processing(self, at: datetime | None = None) -> None:
        """Mueve un trabajo pendiente a procesamiento e incrementa intentos."""
        if self.status is not GenerationStatus.PENDING:
            raise InvalidGenerationJobTransition("Solo un trabajo pendiente puede iniciarse.")
        self.status = GenerationStatus.PROCESSING
        self.started_at = at or datetime.now(UTC)
        self.attempts += 1

    def mark_succeeded(self, result: dict[str, Any], at: datetime | None = None) -> None:
        """Completa un trabajo en curso y persiste su resultado."""
        if self.status is not GenerationStatus.PROCESSING:
            raise InvalidGenerationJobTransition("Solo un trabajo en curso puede completarse.")
        self.result = result
        self.error_message = None
        self.status = GenerationStatus.SUCCEEDED
        self.completed_at = at or datetime.now(UTC)

    def mark_failed(self, message: str, at: datetime | None = None) -> None:
        """Marca como fallido un trabajo en curso y guarda el motivo."""
        if self.status is not GenerationStatus.PROCESSING:
            raise InvalidGenerationJobTransition("Solo un trabajo en curso puede fallar.")
        self.error_message = message[:2000]
        self.status = GenerationStatus.FAILED
        self.completed_at = at or datetime.now(UTC)
