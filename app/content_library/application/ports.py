"""Puertos de persistencia e integración explícita de ContentLibrary."""

from typing import Protocol
from uuid import UUID

from app.content_library.domain.models import (
    LibraryItem,
    LibraryItemType,
    ResolvedLibraryResource,
)


class LibraryRepository(Protocol):
    def add(self, item: LibraryItem) -> None: ...

    def get(self, item_id: UUID, owner_id: UUID) -> LibraryItem | None: ...

    def list(
        self,
        owner_id: UUID,
        item_type: LibraryItemType | None,
        query: str | None,
        favorite: bool | None,
    ) -> list[LibraryItem]: ...

    def save(self, item: LibraryItem) -> None: ...

    def delete(self, item_id: UUID, owner_id: UUID) -> bool: ...


class LibraryResourceResolver(Protocol):
    def resolve(
        self, owner_id: UUID, item_type: LibraryItemType, resource_id: UUID
    ) -> ResolvedLibraryResource | None: ...
