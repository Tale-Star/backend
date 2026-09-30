"""Tests rápidos de las traducciones hacia los contratos oficiales de modelos."""

from __future__ import annotations

import io
import json
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import app.generative_media.infrastructure.acestep_adapter as acestep_module
import app.generative_media.infrastructure.zimage_adapter as zimage_module
from app.generative_media.domain.generation_job import GenerationType
from app.generative_media.infrastructure.acestep_adapter import (
    AceStepAdapter,
    build_acestep_caption,
    build_acestep_lyrics,
    music_language_code,
)
from app.generative_media.infrastructure.generation_queue_lock import FileGenerationQueueLock
from app.generative_media.infrastructure.generation_runtime import SequentialGenerationRuntime
from app.generative_media.infrastructure.style_profiles import (
    StyleProfileConfiguration,
    StyleProfileRegistry,
)
from app.generative_media.infrastructure.zimage_adapter import ZImageAdapter, build_zimage_prompt
from app.shared.config.settings import Settings


def test_zimage_prompt_maps_frontend_fields_in_stable_order() -> None:
    prompt = build_zimage_prompt(
        {
            "Characters": ["Mira", "Pip"],
            "Action": "walking",
            "Emotion": "joyful",
            "Scene": "a garden",
            "Moment": "sunset",
            "Objects": ["lantern"],
            "Extra": "soft light",
            "FreePrompt": "storybook",
        },
        StyleProfileConfiguration(prompt_instruction="Watercolor, hand painted"),
    )

    assert prompt == (
        "Characters: Mira, Pip. Action: walking. Emotion: joyful. Scene: a garden. "
        "Moment: sunset. Objects: lantern. Additional details: soft light. "
        "Creative prompt: storybook. Watercolor, hand painted"
    )


def test_style_profile_registry_keeps_runtime_settings_private(tmp_path) -> None:
    profile_file = tmp_path / "profiles.json"
    profile_file.write_text(
        '{"Watercolor": {"prompt": "soft paint", "lora_path": "models/style.safetensors", '
        '"lora_scale": 0.7}}',
        encoding="utf-8",
    )
    registry = StyleProfileRegistry(profile_file)

    profile = registry.resolve("watercolor")

    assert profile.prompt_instruction == "soft paint"
    assert profile.lora_path == (tmp_path / "models/style.safetensors").resolve()
    assert profile.lora_scale == 0.7


def test_acestep_caption_is_deterministic_and_includes_voice() -> None:
    payload = {
        "Caption": "A night song",
        "Genre": ["folk", "dream pop"],
        "Mood": ["hopeful"],
        "Instruments": ["piano"],
        "Production": ["warm"],
        "Voice": "Female · Powerful",
    }

    caption = build_acestep_caption(payload)

    assert caption == (
        "A night song; Genre: folk, dream pop; Mood: hopeful; Instruments: piano; "
        "Production: warm; Vocal direction: Female · Powerful"
    )
    assert caption == build_acestep_caption(payload)


def test_acestep_maps_structured_lyrics_language_and_instrumental() -> None:
    payload = {
        "Output": "song",
        "Sections": [
            {"Type": "Verse", "Modifier": "soft", "Text": "Buenas noches"},
            {"Type": "Chorus", "Modifier": "powerful", "Text": "Vamos a soñar"},
        ],
    }

    assert build_acestep_lyrics(payload) == (
        "[Verse: soft]\nBuenas noches\n\n[Chorus: powerful]\nVamos a soñar"
    )
    assert build_acestep_lyrics({"Output": "instrumental", "Sections": []}) == "[Instrumental]"
    assert music_language_code("Español") == "es"
    assert music_language_code("English") == "en"


def test_acestep_adapter_passes_turbo_parameters_to_public_inference_api(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {"initialization": [], "calls": []}

    class FakeHandler:
        def initialize_service(self, **kwargs: Any) -> tuple[str, bool]:
            captured["initialization"].append(kwargs)
            return "initialized", True

    class FakeGenerationParams:
        def __init__(self, **kwargs: Any) -> None:
            self.values = kwargs

    class FakeGenerationConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.values = kwargs

    class FakeInference:
        GenerationParams = FakeGenerationParams
        GenerationConfig = FakeGenerationConfig

        @staticmethod
        def generate_music(
            handler: Any,
            llm_handler: Any,
            params: FakeGenerationParams,
            config: FakeGenerationConfig,
            save_dir: str,
        ) -> SimpleNamespace:
            captured["calls"].append((handler, llm_handler, params.values, config.values))
            output_path = Path(save_dir) / "generated.flac"
            output_path.write_bytes(b"fLaCfake-audio")
            return SimpleNamespace(
                success=True,
                error=None,
                status_message="done",
                audios=[{"path": str(output_path)}],
            )

    handler_module = SimpleNamespace(AceStepHandler=FakeHandler)

    def fake_import(module_name: str) -> Any:
        return {
            "acestep.handler": handler_module,
            "acestep.inference": FakeInference,
        }[module_name]

    monkeypatch.setattr(acestep_module, "import_module", fake_import)
    settings = Settings(
        acestep_project_root=tmp_path,
        media_directory=tmp_path / "media",
        model_cache_directory=tmp_path / "cache",
    )
    adapter = AceStepAdapter(settings)

    spanish_song = {
        "Caption": "A gentle night song",
        "Duration": 45,
        "Bpm": 96,
        "Voice": "Female · Soft",
        "Language": "Español",
        "Output": "song",
        "Genre": ["folk"],
        "Mood": ["hopeful"],
        "Instruments": ["piano"],
        "Production": ["warm"],
        "Sections": [{"Type": "Verse", "Modifier": "soft", "Text": "Buenas noches"}],
    }
    song_result = adapter.generate(spanish_song, 123)
    _, song_llm, song_params, song_config = captured["calls"][-1]

    assert captured["initialization"][0]["config_path"] == "acestep-v15-turbo"
    assert song_llm is None
    assert song_params["thinking"] is False
    assert song_config["batch_size"] == 1
    assert song_config["audio_format"] == "flac"
    assert song_params["inference_steps"] == 8
    assert song_params["shift"] == 3.0
    assert song_params["duration"] == 45.0
    assert song_params["bpm"] == 96
    assert song_params["seed"] == 123
    assert song_params["vocal_language"] == "es"
    assert song_params["instrumental"] is False
    assert song_params["caption"] == build_acestep_caption(spanish_song)
    assert song_params["lyrics"] == "[Verse: soft]\nBuenas noches"
    assert song_result.extension == ".flac"
    assert song_result.seed == 123

    english_instrumental = {
        **spanish_song,
        "Language": "English",
        "Output": "instrumental",
        "Sections": [],
    }
    adapter.generate(english_instrumental, 321)
    _, _, instrumental_params, instrumental_config = captured["calls"][-1]

    assert instrumental_params["vocal_language"] == "en"
    assert instrumental_params["instrumental"] is True
    assert instrumental_params["lyrics"] == "[Instrumental]"
    assert instrumental_params["seed"] == 321
    assert instrumental_config["audio_format"] == "flac"


def test_zimage_adapter_preserves_seed_and_style_profile(tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.json"
    lora_path = tmp_path / "watercolor.safetensors"
    lora_path.write_bytes(b"local test profile")
    profile_file.write_text(
        json.dumps(
            {
                "Watercolor": {
                    "prompt": "soft watercolor textures",
                    "lora_path": lora_path.name,
                    "lora_scale": 0.7,
                }
            }
        ),
        encoding="utf-8",
    )
    adapter = ZImageAdapter(
        Settings(model_cache_directory=tmp_path / "cache"),
        StyleProfileRegistry(profile_file),
    )
    image_pipeline = _FakeZImagePipeline()
    torch = _FakeTorch()
    adapter._pipeline = image_pipeline
    adapter._torch = torch
    adapter._device = "cpu"

    result = adapter.generate(
        {
            "Characters": ["Mira"],
            "Action": "walking",
            "Emotion": "joyful",
            "Scene": "a garden",
            "Moment": "sunset",
            "Objects": ["lantern"],
            "Extra": "soft light",
            "FreePrompt": "storybook illustration",
            "Style": "Watercolor",
        },
        42,
    )

    assert torch.generator.seed == 42
    assert image_pipeline.arguments["generator"] is torch.generator
    assert image_pipeline.arguments["num_inference_steps"] == 8
    assert "Visual style" not in image_pipeline.arguments["prompt"]
    assert "soft watercolor textures" in image_pipeline.arguments["prompt"]
    assert image_pipeline.loaded_lora == (str(lora_path.resolve()), "talestar-style-profile")
    assert image_pipeline.active_adapter == ("talestar-style-profile", 0.7)
    assert result.seed == 42
    assert result.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_zimage_load_uses_diffusers_supported_torch_dtype_argument(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}
    fake_dtype = object()
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False), float32=fake_dtype
    )

    class FakePipeline:
        @classmethod
        def from_pretrained(cls, model_path: str, **kwargs: Any) -> FakePipeline:
            captured["model_path"] = model_path
            captured.update(kwargs)
            return cls()

        def to(self, device: str) -> None:
            assert device == "cpu"

    monkeypatch.setattr(
        zimage_module,
        "import_module",
        lambda module_name: {
            "torch": fake_torch,
            "diffusers": SimpleNamespace(ZImagePipeline=FakePipeline),
        }[module_name],
    )
    adapter = ZImageAdapter(
        Settings(
            zimage_model_path=str(tmp_path / "z-image"),
            zimage_device="cpu",
            zimage_dtype="float32",
            zimage_cpu_offload=False,
            model_cache_directory=tmp_path / "cache",
        )
    )

    adapter.load()

    assert captured["torch_dtype"] is fake_dtype
    assert "dtype" not in captured
    assert captured["local_files_only"] is True


def test_fake_generators_remain_usable_without_model_runtime() -> None:
    from app.generative_media.infrastructure.fake_generators import (
        FakeImageGeneratorAdapter,
        FakeMusicGeneratorAdapter,
    )

    image = FakeImageGeneratorAdapter().generate({"FreePrompt": "a tiny star"}, 8)
    music = FakeMusicGeneratorAdapter().generate({"Duration": 10, "Bpm": 80}, 9)

    assert image.content.startswith(b"<svg")
    assert image.seed == 8
    assert music.content.startswith(b"RIFF")
    assert music.seed == 9


def test_generation_runtime_unloads_old_model_before_loading_next() -> None:
    events: list[str] = []
    image = _RecordingRuntimeAdapter("image", events)
    music = _RecordingRuntimeAdapter("music", events)
    runtime = SequentialGenerationRuntime(image, music)

    runtime.activate(GenerationType.IMAGE)
    runtime.activate(GenerationType.IMAGE)
    runtime.activate(GenerationType.MUSIC)
    runtime.release()

    assert events == [
        "image.load",
        "image.unload",
        "music.load",
        "music.unload",
    ]


def test_gpu_queue_lock_allows_only_one_worker_at_a_time(tmp_path) -> None:
    first = FileGenerationQueueLock(tmp_path / "gpu.lock")
    second = FileGenerationQueueLock(tmp_path / "gpu.lock")

    assert first.try_acquire()
    assert not second.try_acquire()
    first.release()
    assert second.try_acquire()
    second.release()


def test_gpu_queue_lock_is_shared_between_processes(tmp_path: Path) -> None:
    lock_path = tmp_path / "gpu.lock"
    lock = FileGenerationQueueLock(lock_path)
    assert lock.try_acquire()
    context = get_context("spawn")

    try:
        assert _try_queue_lock_in_process(context, lock_path) is False
    finally:
        lock.release()

    assert _try_queue_lock_in_process(context, lock_path) is True


class _RecordingRuntimeAdapter:
    def __init__(self, name: str, events: list[str]) -> None:
        self._name = name
        self._events = events

    def load(self) -> None:
        self._events.append(f"{self._name}.load")

    def unload(self) -> None:
        self._events.append(f"{self._name}.unload")


def _try_queue_lock_in_process(context: Any, lock_path: Path) -> bool:
    result_queue = context.Queue()
    process = context.Process(
        target=_try_queue_lock,
        args=(str(lock_path), result_queue),
    )
    process.start()
    try:
        acquired = result_queue.get(timeout=10)
        process.join(timeout=10)
        assert process.exitcode == 0
        return acquired
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
        result_queue.close()


def _try_queue_lock(lock_path: str, result_queue: Any) -> None:
    lock = FileGenerationQueueLock(Path(lock_path))
    acquired = lock.try_acquire()
    result_queue.put(acquired)
    if acquired:
        lock.release()


class _FakeTorch:
    def __init__(self) -> None:
        self.generator = _FakeGenerator()

    def Generator(self, device: str) -> _FakeGenerator:
        assert device == "cpu"
        return self.generator


class _FakeGenerator:
    seed: int | None = None

    def manual_seed(self, seed: int) -> _FakeGenerator:
        self.seed = seed
        return self


class _FakeImage:
    width = 512
    height = 512

    def save(self, output: io.BytesIO, format: str) -> None:
        assert format == "PNG"
        output.write(b"\x89PNG\r\n\x1a\n")


class _FakeZImagePipeline:
    def __init__(self) -> None:
        self.arguments: dict[str, Any] = {}
        self.loaded_lora: tuple[str, str] | None = None
        self.active_adapter: tuple[str, float] | None = None

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.arguments = kwargs
        return SimpleNamespace(images=[_FakeImage()])

    def load_lora_weights(self, path: str, adapter_name: str) -> None:
        self.loaded_lora = (path, adapter_name)

    def set_adapters(self, adapter_name: str, adapter_weights: float) -> None:
        self.active_adapter = (adapter_name, adapter_weights)
