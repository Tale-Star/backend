"""Puerto de almacenamiento para archivos de medios."""

from typing import BinaryIO, Protocol
from uuid import UUID


class AssetStorage(Protocol):
    """Operaciones locales o remotas para almacenar y leer assets propios."""

    def save(
        self, asset_id: UUID, extension: str, content: bytes, owner_id: UUID | None = None
    ) -> str:
        """Guarda bytes y devuelve una clave relativa estable."""
        ...

    def open(self, asset_id: UUID, extension: str, owner_id: UUID | None = None) -> BinaryIO:
        """Abre un asset para lectura binaria."""
        ...

    def open_key(self, relative_key: str, owner_id: UUID | None = None) -> BinaryIO:
        """Abre un asset por su clave opaca validando ownership."""
        ...

    def delete(self, asset_id: UUID, extension: str) -> None:
        """Elimina un asset si existe."""
        ...
