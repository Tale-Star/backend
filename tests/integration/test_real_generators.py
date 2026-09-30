"""Pruebas optativas contra modelos configurados en disco, nunca descarga tests."""

import os
from pathlib import Path

import pytest

from app.generative_media.infrastructure.acestep_adapter import AceStepAdapter
from app.generative_media.infrastructure.zimage_adapter import ZImageAdapter
from app.shared.config.settings import Settings

pytestmark = [
    pytest.mark.model_integration,
    pytest.mark.skipif(
        os.environ.get("RUN_REAL_MODEL_INTEGRATION") != "1",
        reason="activa RUN_REAL_MODEL_INTEGRATION=1 para usar modelos locales",
    ),
]


def test_local_zimage_model_generates_png() -> None:
    settings = Settings(model_downloads_enabled=False)
    if settings.image_generator != "zimage":
        pytest.skip("IMAGE_GENERATOR debe ser zimage")
    if not Path(settings.zimage_model_path).expanduser().is_dir():
        pytest.skip("ZIMAGE_MODEL_PATH debe apuntar a pesos locales ya instalados")
    adapter = ZImageAdapter(settings)
    try:
        result = adapter.generate(
            {"FreePrompt": "small red apple on a white table", "Style": "photorealistic"}, 13
        )
        assert result.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert result.width == settings.zimage_width
        assert result.height == settings.zimage_height
    finally:
        adapter.unload()


def test_local_acestep_model_generates_audio() -> None:
    settings = Settings(model_downloads_enabled=False)
    if settings.music_generator != "acestep":
        pytest.skip("MUSIC_GENERATOR debe ser acestep")
    project_root = settings.acestep_project_root
    if (
        project_root is None
        or not Path(project_root).is_dir()
        or not (Path(project_root) / "checkpoints").is_dir()
    ):
        pytest.skip("ACESTEP_PROJECT_ROOT debe tener checkpoints ACE-Step locales")
    adapter = AceStepAdapter(settings)
    try:
        result = adapter.generate(
            {
                "Caption": "A calm piano lullaby",
                "Duration": 10,
                "Bpm": 72,
                "Voice": "",
                "Language": "English",
                "Output": "instrumental",
                "Genre": ["ambient"],
                "Mood": ["calm"],
                "Instruments": ["piano"],
                "Production": [],
                "Sections": [],
            },
            17,
        )
        assert result.content.startswith(b"fLaC")
        assert result.extension == ".flac"
        assert result.media_type == "audio/flac"
        assert result.duration == 10.0
        assert result.bpm == 72
    finally:
        adapter.unload()
