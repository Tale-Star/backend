"""Adaptador SQLAlchemy para las referencias de biblioteca."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.content_library.application.ports import LibraryRepository
from app.content_library.domain.errors import LibraryItemAlreadySaved
from app.content_library.domain.models import LibraryItem, LibraryItemType
from app.content_library.infrastructure.models import LibraryItemRecord


class SqlAlchemyLibraryRepository(LibraryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: LibraryItem) -> None:
        self._session.add(_to_record(item))
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            if "content_library_items.owner_id" in str(error):
                raise LibraryItemAlreadySaved from error
            raise

    def get(self, item_id: UUID, owner_id: UUID) -> LibraryItem | None:
        record = self._session.scalar(
            select(LibraryItemRecord).where(
                LibraryItemRecord.id == item_id, LibraryItemRecord.owner_id == owner_id
            )
        )
        return _to_domain(record) if record is not None else None

    def list(
        self,
        owner_id: UUID,
        item_type: LibraryItemType | None,
        query: str | None,
        favorite: bool | None,
    ) -> list[LibraryItem]:
        statement = select(LibraryItemRecord).where(LibraryItemRecord.owner_id == owner_id)
        if item_type is not None:
            statement = statement.where(LibraryItemRecord.item_type == item_type.value)
        if favorite is not None:
            statement = statement.where(LibraryItemRecord.favorite.is_(favorite))
        if query:
            pattern = f"%{query.strip().casefold()}%"
            statement = statement.where(
                func.lower(LibraryItemRecord.name).like(pattern)
                | func.lower(LibraryItemRecord.description).like(pattern)
            )
        records = self._session.scalars(
            statement.order_by(LibraryItemRecord.created_at.desc(), LibraryItemRecord.id)
        ).all()
        return [_to_domain(record) for record in records]

    def save(self, item: LibraryItem) -> None:
        record = self._session.scalar(
            select(LibraryItemRecord).where(
                LibraryItemRecord.id == item.id, LibraryItemRecord.owner_id == item.owner_id
            )
        )
        if record is None:
            raise LookupError(f"LibraryItem {item.id} does not exist")
        record.name = item.name
        record.description = item.description
        record.favorite = item.favorite
        record.updated_at = item.updated_at
        self._commit()

    def delete(self, item_id: UUID, owner_id: UUID) -> bool:
        record = self._session.scalar(
            select(LibraryItemRecord).where(
                LibraryItemRecord.id == item_id, LibraryItemRecord.owner_id == owner_id
            )
        )
        if record is None:
            return False
        self._session.delete(record)
        self._commit()
        return True

    def _commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise


def _to_record(item: LibraryItem) -> LibraryItemRecord:
    return LibraryItemRecord(
        id=item.id,
        owner_id=item.owner_id,
        item_type=item.item_type.value,
        resource_id=item.resource_id,
        name=item.name,
        description=item.description,
        resource_path=item.resource_path,
        media_type=item.media_type,
        favorite=item.favorite,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_domain(record: LibraryItemRecord) -> LibraryItem:
    return LibraryItem(
        id=record.id,
        owner_id=record.owner_id,
        item_type=LibraryItemType(record.item_type),
        resource_id=record.resource_id,
        name=record.name,
        description=record.description,
        resource_path=record.resource_path,
        media_type=record.media_type,
        favorite=record.favorite,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
