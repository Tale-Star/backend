"""Procesador de un job por iteración, compartido por el worker local."""

import logging
from typing import Any
from uuid import UUID, uuid4

from app.generative_media.application.asset_storage import AssetStorage
from app.generative_media.application.generation_ports import (
    GeneratedMedia,
    GenerationJobRepository,
    GenerationQueueLockPort,
    GenerationRuntimePort,
    ImageGeneratorPort,
    MusicGeneratorPort,
)
from app.generative_media.domain.generation_job import GenerationJob, GenerationType

logger = logging.getLogger(__name__)


class GenerationWorker:
    """Reclama y procesa trabajos usando adaptadores inyectados."""

    def __init__(
        self,
        jobs: GenerationJobRepository,
        image_generator: ImageGeneratorPort,
        music_generator: MusicGeneratorPort,
        asset_storage: AssetStorage,
        runtime: GenerationRuntimePort | None = None,
        queue_lock: GenerationQueueLockPort | None = None,
    ) -> None:
        self._jobs = jobs
        self._image_generator = image_generator
        self._music_generator = music_generator
        self._asset_storage = asset_storage
        self._runtime = runtime
        self._queue_lock = queue_lock

    def run_once(self) -> UUID | None:
        """Procesa el siguiente trabajo y devuelve su ID, si había uno pendiente."""
        if self._queue_lock is not None and not self._queue_lock.try_acquire():
            return None
        try:
            return self._run_locked()
        finally:
            if self._queue_lock is not None:
                self._queue_lock.release()

    def release(self) -> None:
        """Libera el modelo activo durante la parada ordenada del worker."""
        if self._runtime is not None:
            self._runtime.release()

    def _run_locked(self) -> UUID | None:
        job = self._jobs.claim_next()
        if job is None:
            return None

        try:
            if self._runtime is not None:
                self._runtime.activate(job.type)
            generated = self._generate(job)
            asset_id = uuid4()
            asset_path = self._asset_storage.save(
                asset_id, generated.extension, generated.content, job.owner_id
            )
            result: dict[str, Any] = {
                "asset_id": str(asset_id),
                "path": asset_path,
                "asset_path": asset_path,
                "media_type": generated.media_type,
                "extension": generated.extension,
                "seed": generated.seed if generated.seed is not None else job.seed,
            }
            if generated.width is not None:
                result["width"] = generated.width
            if generated.height is not None:
                result["height"] = generated.height
            if generated.duration is not None:
                result["duration"] = generated.duration
            if generated.bpm is not None:
                result["bpm"] = generated.bpm
            if generated.language is not None:
                result["language"] = generated.language
            job.mark_succeeded(result)
        except KeyboardInterrupt:
            job.mark_failed("Generation interrupted by worker shutdown.")
            self._jobs.save(job)
            raise
        except Exception as error:
            job.mark_failed(str(error) or error.__class__.__name__)
            logger.exception("Falló GenerationJob %s", job.id)

        self._jobs.save(job)
        return job.id

    def _generate(self, job: GenerationJob) -> GeneratedMedia:
        if job.type is GenerationType.IMAGE:
            return self._image_generator.generate(job.payload, job.seed)
        if job.type is GenerationType.MUSIC:
            return self._music_generator.generate(job.payload, job.seed)
        raise ValueError(f"Tipo de generación no soportado: {job.type}")
