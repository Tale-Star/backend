"""Schemas públicos de ContentLibrary."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.content_library.domain.models import LibraryItemType

LibraryItemName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class LibraryItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: LibraryItemType
    resource_id: UUID
    name: LibraryItemName | None = None
    description: str = Field(default="", max_length=5000)


class LibraryItemPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: LibraryItemName | None = None
    description: str | None = Field(default=None, max_length=5000)
    favorite: bool | None = None


class LibraryItemResponse(BaseModel):
    id: UUID
    type: LibraryItemType
    resource_id: UUID
    name: str
    description: str
    favorite: bool
    resource_url: str
    media_type: str | None
    created_at: datetime
    updated_at: datetime
