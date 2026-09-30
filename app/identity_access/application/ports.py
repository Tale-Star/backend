"""Ports requeridos por los casos de uso de identidad."""

from typing import Protocol
from uuid import UUID

from app.identity_access.domain.user import User


class UserRepository(Protocol):
    def add(self, user: User) -> None: ...

    def get(self, user_id: UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def save(self, user: User) -> None: ...


class PasswordHasherPort(Protocol):
    def hash(self, value: str) -> str: ...

    def verify(self, value: str, encoded_hash: str) -> bool: ...


class AccessTokenPort(Protocol):
    def issue(self, subject: UUID) -> str: ...

    def subject(self, token: str) -> UUID | None: ...
