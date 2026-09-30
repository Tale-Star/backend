"""Creación del engine, configuración WAL y sesiones SQLAlchemy."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.shared.config.settings import Settings


def create_database_engine(settings: Settings) -> Engine:
    """Crea el engine y activa pragmas seguros para SQLite local."""
    url = make_url(settings.database_url)
    connect_args: dict[str, object] = {}
    is_memory_database = False

    if url.get_backend_name() == "sqlite":
        connect_args = {
            "check_same_thread": False,
            "timeout": settings.sqlite_busy_timeout_ms / 1000,
        }
        database = url.database
        is_memory_database = database in (None, "", ":memory:") or url.query.get("mode") == "memory"
        if database and not is_memory_database and not database.startswith("file:"):
            Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)

    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(f"PRAGMA busy_timeout = {settings.sqlite_busy_timeout_ms}")
            if not is_memory_database:
                cursor.execute("PRAGMA journal_mode = WAL")
                cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Crea una fábrica de sesiones con commits explícitos en los casos de uso."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """Dependencia FastAPI que cierra la sesión al terminar la solicitud."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session
