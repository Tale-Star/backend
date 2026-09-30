"""Adaptador SQLAlchemy del puerto GenerationJobRepository."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.generative_media.application.generation_ports import (
    GenerationJobRepository,
    StoredMediaAsset,
)
from app.generative_media.domain.generation_job import (
    GenerationJob,
    GenerationStatus,
    GenerationType,
)
from app.generative_media.infrastructure.generation_job_model import GenerationJobRecord


class SqlAlchemyGenerationJobRepository(GenerationJobRepository):
    """Persiste jobs y los reclama con un único UPDATE condicional atómico."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: GenerationJob) -> None:
        self._session.add(self._to_record(job))
        self._session.commit()

    def get(self, job_id: UUID, owner_id: UUID | None = None) -> GenerationJob | None:
        if owner_id is None:
            record = self._session.get(GenerationJobRecord, job_id)
        else:
            record = self._session.scalar(
                select(GenerationJobRecord).where(
                    GenerationJobRecord.id == job_id,
                    GenerationJobRecord.owner_id == owner_id,
                )
            )
        return self._to_domain(record) if record is not None else None

    def get_asset(self, asset_id: UUID, owner_id: UUID) -> StoredMediaAsset | None:
        record = self._session.scalar(
            select(GenerationJobRecord).where(
                GenerationJobRecord.owner_id == owner_id,
                GenerationJobRecord.status == GenerationStatus.SUCCEEDED.value,
                GenerationJobRecord.result["asset_id"].as_string() == str(asset_id),
            )
        )
        if record is None or record.result is None:
            return None
        path = record.result.get("path")
        media_type = record.result.get("media_type")
        if not isinstance(path, str) or not isinstance(media_type, str):
            return None
        return StoredMediaAsset(id=asset_id, path=path, media_type=media_type)

    def save(self, job: GenerationJob) -> None:
        record = self._session.get(GenerationJobRecord, job.id)
        if record is None:
            raise LookupError(f"GenerationJob {job.id} does not exist")
        self._copy_to_record(job, record)
        self._session.commit()

    def claim_next(self) -> GenerationJob | None:
        """Atomically changes one oldest Pending row to Processing."""
        candidate_id = (
            select(GenerationJobRecord.id)
            .where(GenerationJobRecord.status == GenerationStatus.PENDING.value)
            .order_by(GenerationJobRecord.created_at, GenerationJobRecord.id)
            .limit(1)
            .scalar_subquery()
        )
        statement = (
            update(GenerationJobRecord)
            .where(
                GenerationJobRecord.id == candidate_id,
                GenerationJobRecord.status == GenerationStatus.PENDING.value,
            )
            .values(
                status=GenerationStatus.PROCESSING.value,
                started_at=datetime.now(UTC),
                attempts=GenerationJobRecord.attempts + 1,
            )
            .returning(GenerationJobRecord.id)
        )
        try:
            job_id = self._session.execute(statement).scalar_one_or_none()
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        if job_id is None:
            return None
        record = self._session.get(GenerationJobRecord, job_id, populate_existing=True)
        if record is None:
            return None
        job = self._to_domain(record)
        self._session.commit()
        return job

    @staticmethod
    def _to_record(job: GenerationJob) -> GenerationJobRecord:
        return GenerationJobRecord(
            id=job.id,
            owner_id=job.owner_id,
            type=job.type.value,
            status=job.status.value,
            payload=job.payload,
            result=job.result,
            error_message=job.error_message,
            seed=job.seed,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            attempts=job.attempts,
        )

    @staticmethod
    def _copy_to_record(job: GenerationJob, record: GenerationJobRecord) -> None:
        record.type = job.type.value
        record.owner_id = job.owner_id
        record.status = job.status.value
        record.payload = job.payload
        record.result = job.result
        record.error_message = job.error_message
        record.seed = job.seed
        record.created_at = job.created_at
        record.started_at = job.started_at
        record.completed_at = job.completed_at
        record.attempts = job.attempts

    @staticmethod
    def _to_domain(record: GenerationJobRecord) -> GenerationJob:
        return GenerationJob(
            id=record.id,
            owner_id=record.owner_id,
            type=GenerationType(record.type),
            status=GenerationStatus(record.status),
            payload=record.payload,
            result=record.result,
            error_message=record.error_message,
            seed=record.seed,
            created_at=_as_utc(record.created_at),
            started_at=_as_optional_utc(record.started_at),
            completed_at=_as_optional_utc(record.completed_at),
            attempts=record.attempts,
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _as_optional_utc(value: datetime | None) -> datetime | None:
    return _as_utc(value) if value is not None else None
