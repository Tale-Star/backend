"""Punto de entrada ASGI y composición de la aplicación."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.health import router as health_router
from app.api.health import versioned_router as versioned_health_router
from app.content_library.interfaces.routes import router as content_library_router
from app.creative_authoring.interfaces.routes import router as creative_authoring_router
from app.generative_media.application.generation_service import GenerationJobService
from app.generative_media.infrastructure.generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.generative_media.infrastructure.local_asset_storage import LocalAssetStorage
from app.generative_media.interfaces.routes import media_router
from app.generative_media.interfaces.routes import router as generation_router
from app.identity_access.interfaces.routes import router as identity_access_router
from app.shared.config.settings import Settings, get_settings
from app.shared.database.session import create_database_engine, create_session_factory
from app.shared.errors import install_exception_handlers
from app.shared.logging import configure_logging


def _build_generation_job_service(session: Session) -> GenerationJobService:
    return GenerationJobService(SqlAlchemyGenerationJobRepository(session))


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construye la aplicación con sus adaptadores y configuración."""
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    engine = create_database_engine(app_settings)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    application = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        debug=app_settings.app_debug,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "API health checks."},
            {"name": "identity-access", "description": "Adult account and parental PIN."},
            {"name": "creative-authoring", "description": "Characters, scenarios and stories."},
            {"name": "generations", "description": "Asynchronous image and music jobs."},
            {"name": "media", "description": "Owned generated media assets."},
            {"name": "content-library", "description": "Saved content references and favorites."},
        ],
    )
    application.state.settings = app_settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    media_storage = LocalAssetStorage(app_settings.media_directory)
    application.state.media_storage = media_storage
    application.state.asset_storage = media_storage
    application.state.generation_job_service_factory = _build_generation_job_service

    smoke_test_page = Path(__file__).resolve().parent.parent / "smoke-test" / "index.html"
    if app_settings.app_env in {"local", "test"} and smoke_test_page.is_file():

        def serve_smoke_test_page() -> FileResponse:
            return FileResponse(smoke_test_page, media_type="text/html")

        application.add_api_route(
            "/smoke-test",
            serve_smoke_test_page,
            methods=["GET"],
            include_in_schema=False,
        )

    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    application.include_router(health_router)
    application.include_router(versioned_health_router, prefix="/api/v1")
    application.include_router(identity_access_router, prefix="/api/v1")
    application.include_router(creative_authoring_router, prefix="/api/v1")
    application.include_router(generation_router, prefix="/api/v1")
    application.include_router(media_router, prefix="/api/v1")
    application.include_router(content_library_router, prefix="/api/v1")
    install_exception_handlers(application)
    logging.getLogger(__name__).info("Tale Star API configurada (%s)", app_settings.app_env)
    return application


app = create_app()
