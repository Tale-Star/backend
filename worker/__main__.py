"""Entrada para `python -m worker`."""

import logging
import time

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
                while True:
                    job_id = processor.run_once()
                    if job_id is None:
                        time.sleep(1)
                    else:
                        logger.info("GenerationJob procesado: %s", job_id)
            finally:
                processor.release()
    except KeyboardInterrupt:
        logger.info("Worker detenido")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
