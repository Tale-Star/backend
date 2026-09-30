"""Entidades de referencias guardadas en la biblioteca del usuario."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from app.shared.domain.entity import Entity


class LibraryItemType(StrEnum):
    IMAGE = "image"
    STORY = "story"
    MUSIC = "music"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False, slots=True)
class LibraryItem(Entity):
    owner_id: UUID
    item_type: LibraryItemType
    resource_id: UUID
    name: str
    description: str = ""
    resource_path: str | None = None
    media_type: str | None = None
    favorite: bool = False
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class ResolvedLibraryResource:
    name: str
    resource_path: str | None = None
    media_type: str | None = None
