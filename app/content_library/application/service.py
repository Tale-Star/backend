"""Casos de uso de biblioteca con referencias validadas y ownership."""

from datetime import UTC, datetime
from uuid import UUID

from app.content_library.application.ports import LibraryRepository, LibraryResourceResolver
from app.content_library.domain.errors import LibraryResourceNotFound
from app.content_library.domain.models import LibraryItem, LibraryItemType


class ContentLibraryService:
    def __init__(self, repository: LibraryRepository, resolver: LibraryResourceResolver) -> None:
        self._repository = repository
        self._resolver = resolver

    def create(
        self,
        owner_id: UUID,
        item_type: LibraryItemType,
        resource_id: UUID,
        name: str | None,
        description: str,
    ) -> LibraryItem:
        resource = self._resolver.resolve(owner_id, item_type, resource_id)
        if resource is None:
            raise LibraryResourceNotFound
        item = LibraryItem(
            owner_id=owner_id,
            item_type=item_type,
            resource_id=resource_id,
            name=(name or resource.name).strip(),
            description=description,
            resource_path=resource.resource_path,
            media_type=resource.media_type,
        )
        self._repository.add(item)
        return item

    def get(self, item_id: UUID, owner_id: UUID) -> LibraryItem | None:
        return self._repository.get(item_id, owner_id)

    def list(
        self,
        owner_id: UUID,
        item_type: LibraryItemType | None = None,
        query: str | None = None,
        favorite: bool | None = None,
    ) -> list[LibraryItem]:
        return self._repository.list(owner_id, item_type, query, favorite)

    def save(self, item: LibraryItem) -> LibraryItem:
        if self._repository.get(item.id, item.owner_id) is None:
            raise LibraryResourceNotFound
        item.updated_at = datetime.now(UTC)
        self._repository.save(item)
        return item

    def delete(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._repository.delete(item_id, owner_id)
