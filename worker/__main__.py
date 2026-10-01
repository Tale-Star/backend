"""Entrada para `python -m worker`."""

import logging
import signal
from threading import Event
from types import FrameType

from app.generative_media.application.generation_worker import GenerationWorker
from app.generative_media.infrastructure.acestep_adapter import AceStepAdapter
from app.generative_media.infrastructure.fake_generators import (
    FakeImageGeneratorAdapter,
    FakeMusicGeneratorAdapter,
)
from app.generative_media.infrastructure.generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.generative_media.infrastructure.generation_queue_lock import FileGenerationQueueLock
from app.generative_media.infrastructure.generation_runtime import (
    SequentialGenerationRuntime,
)
from app.generative_media.infrastructure.local_asset_storage import LocalAssetStorage
from app.generative_media.infrastructure.zimage_adapter import ZImageAdapter
from app.shared.config.settings import get_settings
from app.shared.database.model_registry import register_models
from app.shared.database.session import create_database_engine, create_session_factory
from app.shared.logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    register_models()
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    shutdown_requested = Event()

    def handle_shutdown_signal(signal_number: int, _frame: FrameType | None) -> None:
        logger.info(
            "Worker recibió señal %s; terminará el trabajo en curso y descargará runtimes",
            signal_number,
        )
        shutdown_requested.set()

    previous_sigint = signal.signal(signal.SIGINT, handle_shutdown_signal)
    previous_sigterm = signal.signal(signal.SIGTERM, handle_shutdown_signal)

    logger.info(
        "Worker iniciado (image=%s, music=%s); media directory: %s",
        settings.image_generator,
        settings.music_generator,
        settings.media_directory,
    )
    image_generator = (
        ZImageAdapter(settings)
        if settings.image_generator == "zimage"
        else FakeImageGeneratorAdapter()
    )
    music_generator = (
        AceStepAdapter(settings)
        if settings.music_generator == "acestep"
        else FakeMusicGeneratorAdapter()
    )
    runtime = SequentialGenerationRuntime(image_generator, music_generator)
    queue_lock = FileGenerationQueueLock(settings.gpu_queue_lock_path)
    try:
        with session_factory() as session:
            processor = GenerationWorker(
                jobs=SqlAlchemyGenerationJobRepository(session),
                image_generator=image_generator,
                music_generator=music_generator,
                asset_storage=LocalAssetStorage(settings.media_directory),
                runtime=runtime,
                queue_lock=queue_lock,
            )
            try:
                while not shutdown_requested.is_set():
                    job_id = processor.run_once()
                    if job_id is None:
                        shutdown_requested.wait(1)
                    else:
                        logger.info("GenerationJob procesado: %s", job_id)
            finally:
                processor.release()
    finally:
        engine.dispose()
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)

    logger.info("Worker detenido limpiamente")


if __name__ == "__main__":
    main()
