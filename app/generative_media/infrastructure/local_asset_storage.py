"""Adaptador de almacenamiento de assets en el filesystem local."""

import re
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from uuid import UUID


class LocalAssetStorage:
    """Escribe assets bajo el directorio configurado, organizados por UUID."""

    _extension_pattern = re.compile(r"\.[a-z0-9]{1,10}\Z")

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def save(
        self, asset_id: UUID, extension: str, content: bytes, owner_id: UUID | None = None
    ) -> str:
        """Guarda un archivo sin permitir rutas aportadas por el cliente."""
        path = self._path_for(asset_id, extension, owner_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = path.parent.resolve(strict=True)
        expected_root = self.root / owner_id.hex if owner_id is not None else self.root
        if owner_id is not None and expected_root.resolve(strict=True) != expected_root:
            raise ValueError("El directorio del usuario no puede ser un enlace simbólico.")
        if not resolved_parent.is_relative_to(expected_root):
            raise ValueError("El directorio del asset debe permanecer en el directorio propio.")
        with path.open("xb") as asset_file:
            asset_file.write(content)
        return path.relative_to(self.root).as_posix()

    def open(self, asset_id: UUID, extension: str, owner_id: UUID | None = None) -> BinaryIO:
        """Abre un archivo guardado para lectura."""
        return self._path_for(asset_id, extension, owner_id).open("rb")

    def resolve_key(self, relative_key: str, owner_id: UUID | None = None) -> Path:
        """Resuelve una clave relativa guardada y rechaza rutas externas."""
        if (
            not relative_key
            or "\\" in relative_key
            or ":" in relative_key
            or "\x00" in relative_key
        ):
            raise ValueError("La clave del asset no es válida.")
        key = PurePosixPath(relative_key)
        if key.is_absolute() or any(part in ("", ".", "..") for part in key.parts):
            raise ValueError("La clave del asset no es válida.")
        if key.as_posix() != relative_key:
            raise ValueError("La clave del asset no es canónica.")
        if owner_id is not None and (not key.parts or key.parts[0] != owner_id.hex):
            raise ValueError("El usuario no es propietario del asset.")

        root = self.root.resolve()
        candidate = (root / Path(*key.parts)).resolve(strict=True)
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError("La clave del asset no es válida.")
        if owner_id is not None and not candidate.is_relative_to(root / owner_id.hex):
            raise ValueError("El usuario no es propietario del asset.")
        return candidate

    def open_key(self, relative_key: str, owner_id: UUID | None = None) -> BinaryIO:
        """Abre una clave validada sin exponer rutas de filesystem al llamador."""
        return self.resolve_key(relative_key, owner_id).open("rb")

    def delete(self, asset_id: UUID, extension: str, owner_id: UUID | None = None) -> None:
        """Elimina un archivo si está presente."""
        self._path_for(asset_id, extension, owner_id).unlink(missing_ok=True)

    def _path_for(self, asset_id: UUID, extension: str, owner_id: UUID | None = None) -> Path:
        normalized_extension = extension.lower()
        if self._extension_pattern.fullmatch(normalized_extension) is None:
            raise ValueError("La extensión del asset debe ser una extensión simple, como '.png'.")
        identifier = asset_id.hex
        if owner_id is not None:
            return self.root / owner_id.hex / identifier[:2] / f"{identifier}{normalized_extension}"
        return self.root / identifier[:2] / f"{identifier}{normalized_extension}"
