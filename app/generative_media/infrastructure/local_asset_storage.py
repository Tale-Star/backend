"""Adaptador de almacenamiento de assets en el filesystem local."""

import re
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


class LocalAssetStorage:
    """Escribe assets bajo el directorio configurado, organizados por UUID."""

    _extension_pattern = re.compile(r"\.[a-z0-9]{1,10}\Z")

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def save(self, asset_id: UUID, extension: str, content: bytes) -> str:
        """Guarda un archivo sin permitir rutas aportadas por el cliente."""
        path = self._path_for(asset_id, extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as asset_file:
            asset_file.write(content)
        return path.relative_to(self.root).as_posix()

    def open(self, asset_id: UUID, extension: str) -> BinaryIO:
        """Abre un archivo guardado para lectura."""
        return self._path_for(asset_id, extension).open("rb")

    def delete(self, asset_id: UUID, extension: str) -> None:
        """Elimina un archivo si está presente."""
        self._path_for(asset_id, extension).unlink(missing_ok=True)

    def _path_for(self, asset_id: UUID, extension: str) -> Path:
        normalized_extension = extension.lower()
        if self._extension_pattern.fullmatch(normalized_extension) is None:
            raise ValueError("La extensión del asset debe ser una extensión simple, como '.png'.")
        identifier = asset_id.hex
        return self.root / identifier[:2] / f"{identifier}{normalized_extension}"

