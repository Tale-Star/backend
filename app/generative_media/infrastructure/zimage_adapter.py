"""Adapter de Z-Image-Turbo usando la API pública de Diffusers."""

from __future__ import annotations

import io
import logging
import os
import secrets
from importlib import import_module
from pathlib import Path
from time import perf_counter
from typing import Any

from app.generative_media.application.generation_ports import GeneratedMedia
from app.generative_media.infrastructure.style_profiles import (
    StyleProfileConfiguration,
    StyleProfileRegistry,
)
from app.shared.config.settings import Settings

logger = logging.getLogger(__name__)


class ZImageAdapter:
    """Genera PNG localmente y mantiene el pipeline cargado hasta cambiar de modelo."""

    _lora_adapter_name = "talestar-style-profile"

    def __init__(
        self,
        settings: Settings,
        style_profiles: StyleProfileRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._style_profiles = style_profiles or StyleProfileRegistry(
            settings.zimage_style_profiles_file
        )
        self._pipeline: Any | None = None
        self._torch: Any | None = None
        self._device: str | None = None
        self._loaded_lora_path: Path | None = None

    def load(self) -> None:
        if self._pipeline is not None:
            return
        load_started = perf_counter()
        self._settings.model_cache_directory.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self._settings.model_cache_directory.resolve()))
        try:
            torch = import_module("torch")
            diffusers = import_module("diffusers")
        except ImportError as error:
            raise RuntimeError(
                "Z-Image requiere PyTorch y Diffusers; instala las dependencias opcionales."
            ) from error

        device = self._resolve_device(torch)
        dtype = self._resolve_dtype(torch, device)
        pipeline_type = getattr(diffusers, "ZImagePipeline", None)
        if pipeline_type is None:
            raise RuntimeError("La versión instalada de Diffusers no expone ZImagePipeline.")

        pipeline = pipeline_type.from_pretrained(
            self._settings.zimage_model_path,
            torch_dtype=dtype,
            cache_dir=str(self._settings.model_cache_directory.resolve()),
            local_files_only=not self._settings.model_downloads_enabled,
        )
        if device == "cuda" and self._settings.zimage_cpu_offload:
            pipeline.enable_model_cpu_offload()
        else:
            pipeline.to(device)
        self._pipeline = pipeline
        self._torch = torch
        self._device = device
        logger.info(
            "Loaded Z-Image-Turbo device=%s dtype=%s cpu_offload=%s load_seconds=%.2f",
            device,
            dtype,
            device == "cuda" and self._settings.zimage_cpu_offload,
            perf_counter() - load_started,
        )

    def unload(self) -> None:
        if self._pipeline is not None and self._loaded_lora_path is not None:
            self._pipeline.unload_lora_weights()
        self._loaded_lora_path = None
        self._pipeline = None
        self._torch = None
        self._device = None

    def generate(self, payload: dict[str, Any], seed: int | None) -> GeneratedMedia:
        self.load()
        if self._pipeline is None or self._torch is None or self._device is None:
            raise RuntimeError("El pipeline Z-Image no está inicializado.")
        if self._settings.zimage_width % 16 or self._settings.zimage_height % 16:
            raise ValueError("ZIMAGE_WIDTH y ZIMAGE_HEIGHT deben ser múltiplos de 16.")

        profile = self._style_profiles.resolve(_text(payload.get("Style")))
        self._apply_style_profile(profile)
        prompt = build_zimage_prompt(payload, profile)
        effective_seed = seed if seed is not None else secrets.randbelow(4_294_967_296)
        generator = self._torch.Generator(device=self._device).manual_seed(effective_seed)
        cuda = getattr(self._torch, "cuda", None)
        cuda_available = self._device == "cuda" and bool(cuda is not None and cuda.is_available())
        if cuda_available and cuda is not None:
            cuda.synchronize()
            cuda.reset_peak_memory_stats()
        generation_started = perf_counter()
        output = self._pipeline(
            prompt=prompt,
            width=self._settings.zimage_width,
            height=self._settings.zimage_height,
            num_inference_steps=self._settings.zimage_inference_steps,
            guidance_scale=0.0,
            generator=generator,
        )
        if cuda_available and cuda is not None:
            cuda.synchronize()
        elapsed_seconds = perf_counter() - generation_started
        image = output.images[0]
        peak_memory_mib = (
            round(cuda.max_memory_reserved() / (1024 * 1024))
            if cuda_available and cuda is not None
            else None
        )
        logger.info(
            "Z-Image-Turbo generation device=%s dtype=%s dimensions=%sx%s seconds=%.2f "
            "cuda_peak_reserved_mib=%s",
            self._device,
            getattr(self._pipeline, "dtype", "configured"),
            image.width,
            image.height,
            elapsed_seconds,
            peak_memory_mib,
        )
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return GeneratedMedia(
            content=buffer.getvalue(),
            extension=".png",
            media_type="image/png",
            seed=effective_seed,
            width=image.width,
            height=image.height,
        )

    def _apply_style_profile(self, profile: StyleProfileConfiguration) -> None:
        if self._pipeline is None:
            raise RuntimeError("El pipeline Z-Image no está inicializado.")
        if profile.lora_path is None:
            if self._loaded_lora_path is not None:
                self._pipeline.unload_lora_weights()
                self._loaded_lora_path = None
            return
        if not profile.lora_path.is_file():
            raise FileNotFoundError(f"No existe el adapter configurado: {profile.lora_path}")
        if profile.lora_path != self._loaded_lora_path:
            if self._loaded_lora_path is not None:
                self._pipeline.unload_lora_weights()
            self._pipeline.load_lora_weights(
                str(profile.lora_path), adapter_name=self._lora_adapter_name
            )
            self._loaded_lora_path = profile.lora_path
        self._pipeline.set_adapters(self._lora_adapter_name, adapter_weights=profile.lora_scale)

    def _resolve_device(self, torch: Any) -> str:
        if self._settings.zimage_device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if self._settings.zimage_device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("ZIMAGE_DEVICE=cuda pero PyTorch no detecta CUDA.")
        return self._settings.zimage_device

    def _resolve_dtype(self, torch: Any, device: str) -> Any:
        requested_dtype = self._settings.zimage_dtype
        if requested_dtype == "auto":
            if device != "cuda":
                requested_dtype = "float32"
            elif torch.cuda.is_bf16_supported():
                requested_dtype = "bfloat16"
            else:
                requested_dtype = "float16"
        return getattr(torch, requested_dtype)


def build_zimage_prompt(
    payload: dict[str, Any], profile: StyleProfileConfiguration | None = None
) -> str:
    """Convierte el contrato público de imagen en prompt ordenado y reproducible."""
    selected_profile = profile or StyleProfileConfiguration(prompt_instruction="")
    parts = [
        _label("Characters", payload.get("Characters")),
        _label("Action", payload.get("Action")),
        _label("Emotion", payload.get("Emotion")),
        _label("Scene", payload.get("Scene")),
        _label("Moment", payload.get("Moment")),
        _label("Objects", payload.get("Objects")),
        _label("Additional details", payload.get("Extra")),
        _label("Creative prompt", payload.get("FreePrompt")),
        selected_profile.prompt_instruction.strip(),
    ]
    prompt = ". ".join(part for part in parts if part)
    return prompt or "A colorful storybook illustration."


def _label(label: str, value: Any) -> str:
    if isinstance(value, list):
        values = [str(item).strip() for item in value if str(item).strip()]
        value_text = ", ".join(values)
    else:
        value_text = _text(value)
    return f"{label}: {value_text}" if value_text else ""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
