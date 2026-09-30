"""Adaptador que valida referencias de Story y GenerationJob entre contextos."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content_library.application.ports import LibraryResourceResolver
from app.content_library.domain.models import LibraryItemType, ResolvedLibraryResource
from app.creative_authoring.infrastructure.models import StoryRecord
from app.generative_media.domain.generation_job import GenerationStatus, GenerationType
from app.generative_media.infrastructure.generation_job_model import GenerationJobRecord


class SqlAlchemyLibraryResourceResolver(LibraryResourceResolver):
    """Integration adapter for the MVP's SQLite-backed contexts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve(
        self, owner_id: UUID, item_type: LibraryItemType, resource_id: UUID
    ) -> ResolvedLibraryResource | None:
        if item_type is LibraryItemType.STORY:
            story = self._session.scalar(
                select(StoryRecord).where(
                    StoryRecord.id == resource_id, StoryRecord.owner_id == owner_id
                )
            )
            return ResolvedLibraryResource(name=story.title) if story is not None else None

        generation_type = (
            GenerationType.IMAGE if item_type is LibraryItemType.IMAGE else GenerationType.MUSIC
        )
        job = self._session.scalar(
            select(GenerationJobRecord).where(
                GenerationJobRecord.owner_id == owner_id,
                GenerationJobRecord.type == generation_type.value,
                GenerationJobRecord.status == GenerationStatus.SUCCEEDED.value,
                GenerationJobRecord.result["asset_id"].as_string() == str(resource_id),
            )
        )
        if job is None or job.result is None:
            return None
        return ResolvedLibraryResource(
            name=f"{item_type.value.title()} {str(resource_id)[:8]}",
            resource_path=job.result.get("path"),
            media_type=job.result.get("media_type"),
        )
