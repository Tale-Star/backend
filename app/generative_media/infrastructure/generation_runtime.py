"""Coordinación de memoria para mantener un solo modelo generativo activo."""

import gc
import sys
from typing import Protocol

from app.generative_media.application.generation_ports import GenerationRuntimePort
from app.generative_media.domain.generation_job import GenerationType


class RuntimeManagedAdapter(Protocol):
    """Ciclo de vida implementado por los adapters con runtime propio."""

    def load(self) -> None: ...

    def unload(self) -> None: ...


class SequentialGenerationRuntime(GenerationRuntimePort):
    """Cambia de modelo liberando el anterior antes de activar el siguiente."""

    def __init__(
        self,
        image_adapter: RuntimeManagedAdapter,
        music_adapter: RuntimeManagedAdapter,
    ) -> None:
        self._adapters = {
            GenerationType.IMAGE: image_adapter,
            GenerationType.MUSIC: music_adapter,
        }
        self._active: GenerationType | None = None

    def activate(self, generation_type: GenerationType) -> None:
        if generation_type is self._active:
            return
        self.release()
        adapter = self._adapters[generation_type]
        adapter.load()
        self._active = generation_type

    def release(self) -> None:
        if self._active is not None:
            self._adapters[self._active].unload()
            self._active = None
        gc.collect()
        _clear_cuda_cache_if_loaded()


def _clear_cuda_cache_if_loaded() -> None:
    """Limpia la caché solo si torch ya se importó y CUDA está disponible."""
    torch = sys.modules.get("torch")
    if torch is None:
        return
    cuda = getattr(torch, "cuda", None)
    try:
        if cuda is not None and cuda.is_available():
            cuda.empty_cache()
    except RuntimeError:
        # Una instalación CPU o un driver desconectado no debe impedir liberar referencias.
        return
