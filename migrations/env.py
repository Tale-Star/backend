"""Configuración Alembic con los mismos settings y pragmas que la API."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Engine as SqlAlchemyEngine

from app.shared.config.settings import get_settings
from app.shared.database.base import Base
from app.shared.database.session import create_database_engine

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta migraciones sin abrir una conexión."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=settings.database_url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones usando el engine compartido de la aplicación."""
    connectable: SqlAlchemyEngine = create_database_engine(settings)
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=settings.database_url.startswith("sqlite"),
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
