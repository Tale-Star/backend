"""Settings cargados desde variables de entorno o un archivo .env local."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de ejecución del backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    app_name: str = "Tale Star API"
    app_env: Literal["local", "test", "production"] = "local"
    app_debug: bool = False
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    database_url: str = "sqlite:///./data/talestar.db"
    assets_directory: Path = Path("./data/assets")
    media_directory: Path = Path("./data/media")
    gpu_queue_lock_path: Path = Path("./data/gpu-queue.lock")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    sqlite_busy_timeout_ms: int = Field(default=5000, gt=0)
    jwt_secret_key: SecretStr = SecretStr(
        "development-only-change-this-jwt-secret-before-deployment-32chars"
    )
    jwt_access_token_minutes: int = Field(default=30, gt=0, le=1440)

    image_generator: Literal["fake", "zimage"] = "fake"
    music_generator: Literal["fake", "acestep"] = "fake"
    model_cache_directory: Path = Path("./data/model-cache")
    model_downloads_enabled: bool = False

    zimage_model_path: str = "Tongyi-MAI/Z-Image-Turbo"
    zimage_device: Literal["auto", "cuda", "cpu"] = "auto"
    zimage_dtype: Literal["auto", "bfloat16", "float16", "float32"] = "auto"
    zimage_cpu_offload: bool = True
    zimage_width: int = Field(default=1024, ge=256, le=1536, multiple_of=16)
    zimage_height: int = Field(default=1024, ge=256, le=1536, multiple_of=16)
    zimage_inference_steps: int = Field(default=8, ge=1, le=50)
    zimage_style_profiles_file: Path | None = None

    acestep_project_root: Path | None = None
    acestep_model_config: str = "acestep-v15-turbo"
    acestep_device: Literal["auto", "cuda", "cpu", "mps", "xpu"] = "auto"
    acestep_offload_to_cpu: bool = True
    acestep_offload_dit_to_cpu: bool = True
    acestep_quantization: Literal["none", "int8_weight_only", "fp8_weight_only", "w8a8_dynamic"] = (
        "none"
    )

    @model_validator(mode="after")
    def validate_production_jwt_secret(self) -> Settings:
        if self.app_env == "production" and self.jwt_secret_key.get_secret_value().startswith(
            "development-only-"
        ):
            raise ValueError("JWT_SECRET_KEY debe configurarse fuera del valor de desarrollo.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Devuelve settings cacheados para el proceso actual."""
    return Settings()
