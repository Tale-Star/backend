"""Puerto de almacenamiento para archivos de medios."""

from typing import BinaryIO, Protocol
from uuid import UUID


class AssetStorage(Protocol):
    """Operaciones locales o remotas para almacenar bytes asociados a un UUID."""

    def save(self, asset_id: UUID, extension: str, content: bytes) -> str:
        """Guarda bytes y devuelve una clave relativa estable."""
        ...

    def open(self, asset_id: UUID, extension: str) -> BinaryIO:
        """Abre un asset para lectura binaria."""
        ...

    def delete(self, asset_id: UUID, extension: str) -> None:
        """Elimina un asset si existe."""
        ...
