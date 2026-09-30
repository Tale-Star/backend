"""Punto de entrada ASGI y composición de la aplicación."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.health import versioned_router as versioned_health_router
from app.shared.config.settings import Settings, get_settings
from app.shared.database.session import create_database_engine, create_session_factory
from app.shared.errors import install_exception_handlers
from app.shared.logging import configure_logging


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
        debug=app_settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.engine = engine
    application.state.session_factory = session_factory

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
    install_exception_handlers(application)
    logging.getLogger(__name__).info("Tale Star API configurada (%s)", app_settings.app_env)
    return application


app = create_app()

