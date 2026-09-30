"""Puertos de aplicación para trabajos, generadores y almacenamiento."""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.generative_media.domain.generation_job import GenerationJob, GenerationType


@dataclass(frozen=True, slots=True)
class GeneratedMedia:
    """Bytes y metadatos listos para persistir como asset local."""

    content: bytes
    extension: str
    media_type: str
    seed: int | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    bpm: int | None = None
    language: str | None = None


@dataclass(frozen=True, slots=True)
class StoredMediaAsset:
    """A user-owned asset reference resolved by a repository adapter."""

    id: UUID
    path: str
    media_type: str


class ImageGeneratorPort(Protocol):
    """Genera una imagen desde el payload validado de un job."""

    def generate(self, payload: dict[str, Any], seed: int | None) -> GeneratedMedia: ...


class MusicGeneratorPort(Protocol):
    """Genera audio desde el payload validado de un job."""

    def generate(self, payload: dict[str, Any], seed: int | None) -> GeneratedMedia: ...


class GenerationJobRepository(Protocol):
    """Persistencia y reclamo atómico de GenerationJob."""

    def add(self, job: GenerationJob) -> None: ...

    def get(self, job_id: UUID, owner_id: UUID | None = None) -> GenerationJob | None: ...

    def get_asset(self, asset_id: UUID, owner_id: UUID) -> StoredMediaAsset | None: ...

    def save(self, job: GenerationJob) -> None: ...

    def claim_next(self) -> GenerationJob | None: ...


class GenerationRuntimePort(Protocol):
    """Activa un solo runtime de modelo y libera sus recursos al detenerse."""

    def activate(self, generation_type: GenerationType) -> None: ...

    def release(self) -> None: ...


class GenerationQueueLockPort(Protocol):
    """Bloqueo entre procesos adquirido antes de reclamar un job GPU."""

    def try_acquire(self) -> bool: ...

    def release(self) -> None: ...
