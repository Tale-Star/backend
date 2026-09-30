"""Adapter de ACE-Step 1.5 Turbo por su API pública de inferencia."""

from __future__ import annotations

import logging
import os
import secrets
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from time import perf_counter
from typing import Any

from app.generative_media.application.generation_ports import GeneratedMedia
from app.shared.config.settings import Settings

logger = logging.getLogger(__name__)


class AceStepAdapter:
    """Genera audio sin iniciar el language model ni usar thinking."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._dit_handler: Any | None = None

    def load(self) -> None:
        if self._dit_handler is not None:
            return
        load_started = perf_counter()
        project_root = self._settings.acestep_project_root
        if project_root is None or not project_root.is_dir():
            raise RuntimeError(
                "Configura ACESTEP_PROJECT_ROOT con la instalación oficial de ACE-Step 1.5."
            )

        resolved_project_root = project_root.expanduser().resolve()
        os.environ["ACESTEP_PROJECT_ROOT"] = str(resolved_project_root)

        cache_directory = self._settings.model_cache_directory.expanduser().resolve()
        cache_directory.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(cache_directory))
        if not self._settings.model_downloads_enabled:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        try:
            handler_module = import_module("acestep.handler")
        except ImportError as error:
            raise RuntimeError(
                "ACE-Step debe estar instalado en el mismo entorno Python que el worker."
            ) from error

        handler_type = getattr(handler_module, "AceStepHandler", None)
        if handler_type is None:
            raise RuntimeError("La instalación de ACE-Step no expone AceStepHandler.")
        handler = handler_type()
        initialize_status, initialized = handler.initialize_service(
            project_root=str(resolved_project_root),
            config_path=self._settings.acestep_model_config,
            device=self._settings.acestep_device,
            use_flash_attention=False,
            compile_model=False,
            offload_to_cpu=self._settings.acestep_offload_to_cpu,
            offload_dit_to_cpu=self._settings.acestep_offload_dit_to_cpu,
            quantization=(
                None
                if self._settings.acestep_quantization == "none"
                else self._settings.acestep_quantization
            ),
        )
        if not initialized:
            raise RuntimeError(f"ACE-Step no pudo inicializarse: {initialize_status}")
        self._dit_handler = handler
        logger.info(
            "Loaded ACE-Step model=%s device=%s dtype=%s load_seconds=%.2f",
            self._settings.acestep_model_config,
            getattr(handler, "device", self._settings.acestep_device),
            getattr(handler, "dtype", "unknown"),
            perf_counter() - load_started,
        )

    def unload(self) -> None:
        self._dit_handler = None

    def generate(self, payload: dict[str, Any], seed: int | None) -> GeneratedMedia:
        self.load()
        if self._dit_handler is None:
            raise RuntimeError("ACE-Step no está inicializado.")
        try:
            inference = import_module("acestep.inference")
        except ImportError as error:
            raise RuntimeError("No se pudo importar la API de inferencia de ACE-Step.") from error

        effective_seed = seed if seed is not None else secrets.randbelow(4_294_967_296)
        language = str(payload.get("Language", "English"))
        language_code = music_language_code(language)
        output = str(payload.get("Output", "song"))
        instrumental = output == "instrumental"
        params = inference.GenerationParams(
            task_type="text2music",
            caption=build_acestep_caption(payload),
            lyrics=build_acestep_lyrics(payload),
            instrumental=instrumental,
            bpm=payload.get("Bpm"),
            # ACE-Step 1.5.2 llama `duration` al campo antes conocido como audio_duration.
            duration=float(payload.get("Duration", 10)),
            vocal_language=language_code,
            seed=effective_seed,
            thinking=False,
            inference_steps=8,
            shift=3.0,
            infer_method="ode",
        )
        config = inference.GenerationConfig(
            batch_size=1,
            audio_format="flac",
            use_random_seed=False,
        )

        torch = sys.modules.get("torch")
        cuda = getattr(torch, "cuda", None)
        cuda_available = bool(cuda is not None and cuda.is_available())
        if cuda_available and cuda is not None:
            cuda.synchronize()
            cuda.reset_peak_memory_stats()
        generation_started = perf_counter()

        staging_root = self._settings.media_directory.expanduser().resolve() / ".staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="acestep-", dir=staging_root) as output_directory:
            result = inference.generate_music(
                self._dit_handler,
                None,
                params,
                config,
                save_dir=output_directory,
            )
            if cuda_available and cuda is not None:
                cuda.synchronize()
            elapsed_seconds = perf_counter() - generation_started
            peak_memory_mib = (
                round(cuda.max_memory_reserved() / (1024 * 1024))
                if cuda_available and cuda is not None
                else None
            )
            logger.info(
                "ACE-Step generation model=%s device=%s dtype=%s seconds=%.2f "
                "cuda_peak_reserved_mib=%s",
                self._settings.acestep_model_config,
                getattr(self._dit_handler, "device", self._settings.acestep_device),
                getattr(self._dit_handler, "dtype", "unknown"),
                elapsed_seconds,
                peak_memory_mib,
            )
            if not result.success:
                message = result.error or result.status_message or "falló la generación de audio"
                raise RuntimeError(f"ACE-Step: {message}")
            if not result.audios:
                raise RuntimeError("ACE-Step terminó sin producir un archivo de audio.")

            generated_path = Path(result.audios[0]["path"]).resolve(strict=True)
            if not generated_path.is_relative_to(Path(output_directory).resolve()):
                raise RuntimeError("ACE-Step devolvió un archivo fuera del directorio temporal.")
            extension = generated_path.suffix.lower()
            if extension not in {".wav", ".flac", ".mp3", ".opus", ".aac"}:
                raise RuntimeError("ACE-Step devolvió un formato de audio no soportado.")
            content = generated_path.read_bytes()

        mime_type = {
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".mp3": "audio/mpeg",
            ".opus": "audio/opus",
            ".aac": "audio/aac",
        }[extension]
        return GeneratedMedia(
            content=content,
            extension=extension,
            media_type=mime_type,
            seed=effective_seed,
            duration=float(payload.get("Duration", 10)),
            bpm=payload.get("Bpm") if isinstance(payload.get("Bpm"), int) else None,
            language=language,
        )


def build_acestep_caption(payload: dict[str, Any]) -> str:
    """Compone el caption con orden fijo y sin invocar ningún modelo de lenguaje."""
    parts: list[str] = []
    base_caption = _text(payload.get("Caption"))
    if base_caption:
        parts.append(base_caption)
    for label, key in (
        ("Genre", "Genre"),
        ("Mood", "Mood"),
        ("Instruments", "Instruments"),
        ("Production", "Production"),
    ):
        values = _string_list(payload.get(key))
        if values:
            parts.append(f"{label}: {', '.join(values)}")
    voice = _text(payload.get("Voice"))
    if voice:
        parts.append(f"Vocal direction: {voice}")
    return "; ".join(parts)[:512] or "Tale Star original music"


def build_acestep_lyrics(payload: dict[str, Any]) -> str:
    """Convierte secciones frontend en etiquetas y texto de lyrics ACE-Step."""
    if payload.get("Output") == "instrumental":
        return "[Instrumental]"
    sections = payload.get("Sections")
    if not isinstance(sections, list):
        return ""
    lyrics: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_type = _text(section.get("Type")) or "Verse"
        modifier = _text(section.get("Modifier"))
        text = _text(section.get("Text"))
        if not text:
            continue
        tag = f"{section_type}: {modifier}" if modifier else section_type
        lyrics.append(f"[{tag}]\n{text}")
    return "\n\n".join(lyrics)[:4096]


def music_language_code(language: str) -> str:
    """Traduce los idiomas del frontend a códigos ISO 639-1 usados por ACE-Step."""
    try:
        return {"Español": "es", "English": "en"}[language]
    except KeyError as error:
        raise ValueError(f"Idioma musical no soportado: {language}") from error


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
