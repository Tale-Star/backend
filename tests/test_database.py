"""Pruebas de configuración de la base de datos SQLite."""

from sqlalchemy import text

from app.shared.config.settings import Settings
from app.shared.database.session import create_database_engine, create_session_factory


def test_sqlite_uses_write_ahead_logging(test_settings: Settings) -> None:
    engine = create_database_engine(test_settings)
    try:
        with engine.connect() as connection:
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
        assert journal_mode == "wal"
    finally:
        engine.dispose()


def test_session_factory_creates_sessions(test_settings: Settings) -> None:
    engine = create_database_engine(test_settings)
    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()

