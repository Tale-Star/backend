"""Bloqueo interproceso de la cola local de inferencia."""

from pathlib import Path

from filelock import FileLock, Timeout

from app.generative_media.application.generation_ports import GenerationQueueLockPort


class FileGenerationQueueLock(GenerationQueueLockPort):
    """Serializa el reclamo e inferencia entre workers en la misma máquina."""

    def __init__(self, path: Path) -> None:
        resolved_path = path.expanduser().resolve()
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(resolved_path))

    def try_acquire(self) -> bool:
        try:
            self._lock.acquire(timeout=0)
        except Timeout:
            return False
        return True

    def release(self) -> None:
        self._lock.release()
