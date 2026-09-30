"""Adaptador SQLAlchemy para el repositorio de usuarios."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identity_access.application.ports import UserRepository
from app.identity_access.domain.errors import EmailAlreadyRegistered
from app.identity_access.domain.user import User
from app.identity_access.infrastructure.user_model import UserRecord


class SqlAlchemyUserRepository(UserRepository):
    """Persiste cuentas en SQLite y protege unicidad aun con registros concurrentes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> None:
        self._session.add(self._to_record(user))
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise EmailAlreadyRegistered from error

    def get(self, user_id: UUID) -> User | None:
        record = self._session.get(UserRecord, user_id)
        return self._to_domain(record) if record is not None else None

    def get_by_email(self, email: str) -> User | None:
        record = self._session.scalar(select(UserRecord).where(UserRecord.email == email))
        return self._to_domain(record) if record is not None else None

    def save(self, user: User) -> None:
        record = self._session.get(UserRecord, user.id)
        if record is None:
            raise LookupError(f"User {user.id} does not exist")
        record.display_name = user.display_name
        record.password_hash = user.password_hash
        record.parental_pin_hash = user.parental_pin_hash
        self._commit()

    def _commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    @staticmethod
    def _to_record(user: User) -> UserRecord:
        return UserRecord(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            parental_pin_hash=user.parental_pin_hash,
            created_at=user.created_at,
        )

    @staticmethod
    def _to_domain(record: UserRecord) -> User:
        return User(
            id=record.id,
            email=record.email,
            display_name=record.display_name,
            password_hash=record.password_hash,
            parental_pin_hash=record.parental_pin_hash,
            created_at=record.created_at,
        )
