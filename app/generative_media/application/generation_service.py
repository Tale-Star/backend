"""Casos de uso para crear y consultar solicitudes de generación."""

from typing import Any
from uuid import UUID

from app.generative_media.application.generation_ports import (
    GenerationJobRepository,
    StoredMediaAsset,
)
from app.generative_media.domain.generation_job import GenerationJob, GenerationType


class GenerationJobService:
    """Coordina casos de uso sin depender de HTTP ni SQLAlchemy."""

    def __init__(self, jobs: GenerationJobRepository) -> None:
        self._jobs = jobs

    def create(
        self,
        generation_type: GenerationType,
        payload: dict[str, Any],
        seed: int | None,
        owner_id: UUID | None = None,
    ) -> GenerationJob:
        job = GenerationJob(type=generation_type, payload=payload, seed=seed, owner_id=owner_id)
        self._jobs.add(job)
        return job

    def get(self, job_id: UUID, owner_id: UUID | None = None) -> GenerationJob | None:
        return self._jobs.get(job_id, owner_id)

    def get_asset(self, asset_id: UUID, owner_id: UUID) -> StoredMediaAsset | None:
        return self._jobs.get_asset(asset_id, owner_id)
