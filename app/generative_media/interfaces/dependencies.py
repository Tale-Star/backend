"""Dependencias HTTP del módulo sin conocimiento de adaptadores concretos."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.generative_media.application.generation_service import GenerationJobService
from app.shared.database.session import get_db_session


def get_generation_job_service(
    request: Request, session: Annotated[Session, Depends(get_db_session)]
) -> GenerationJobService:
    """Resuelve el caso de uso compuesto en el bootstrap de la aplicación."""
    factory: Callable[[Session], GenerationJobService] = (
        request.app.state.generation_job_service_factory
    )
    return factory(session)
