"""Fixtures compartidas de tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.shared.config.settings import Settings
from app.shared.database.base import Base


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Configuración aislada para pruebas que no debe tocar data/ local."""
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        assets_directory=tmp_path / "assets",
        media_directory=tmp_path / "media",
        gpu_queue_lock_path=tmp_path / "gpu-queue.lock",
        cors_origins=["http://localhost:5173"],
        model_downloads_enabled=False,
    )


@pytest.fixture
def api_app(test_settings: Settings) -> Iterator[FastAPI]:
    """Aplicación con esquema temporal para las pruebas de integración."""
    application = create_app(test_settings)
    Base.metadata.create_all(application.state.engine)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def api_client(api_app: FastAPI) -> Iterator[TestClient]:
    """Cliente HTTP de pruebas con lifespan habilitado."""
    with TestClient(api_app) as client:
        yield client


@pytest.fixture
def auth_headers(api_client: TestClient) -> dict[str, str]:
    response = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "display_name": "Test Account",
            "password": "test-password-123",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
