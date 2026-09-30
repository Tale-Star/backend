"""Fixtures compartidas de tests."""

from pathlib import Path

import pytest

from app.shared.config.settings import Settings


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Configuración aislada para pruebas que no debe tocar data/ local."""
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        assets_directory=tmp_path / "assets",
        cors_origins=["http://localhost:5173"],
    )
