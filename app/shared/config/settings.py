"""Settings cargados desde variables de entorno o un archivo .env local."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de ejecución del backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Tale Star API"
    app_env: Literal["local", "test", "production"] = "local"
    app_debug: bool = False
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    database_url: str = "sqlite:///./data/talestar.db"
    assets_directory: Path = Path("./data/assets")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    sqlite_busy_timeout_ms: int = Field(default=5000, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Devuelve settings cacheados para el proceso actual."""
    return Settings()
