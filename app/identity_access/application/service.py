"""Casos de uso de registro, login, perfil y PIN parental."""

from uuid import UUID

from app.identity_access.application.ports import (
    AccessTokenPort,
    PasswordHasherPort,
    UserRepository,
)
from app.identity_access.domain.errors import EmailAlreadyRegistered, InvalidCredentials
from app.identity_access.domain.user import User


class IdentityAccessService:
    """Coordina cuentas adultas sin depender de FastAPI ni de SQLAlchemy."""

    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasherPort,
        tokens: AccessTokenPort,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._tokens = tokens

    def register(
        self,
        email: str,
        display_name: str,
        password: str,
        parental_pin: str | None,
    ) -> tuple[User, str]:
        normalized_email = email.strip().casefold()
        if self._users.get_by_email(normalized_email) is not None:
            raise EmailAlreadyRegistered
        user = User(
            email=normalized_email,
            display_name=display_name.strip(),
            password_hash=self._password_hasher.hash(password),
            parental_pin_hash=(
                self._password_hasher.hash(parental_pin) if parental_pin is not None else None
            ),
        )
        self._users.add(user)
        return user, self._tokens.issue(user.id)

    def login(self, email: str, password: str) -> tuple[User, str]:
        user = self._users.get_by_email(email.strip().casefold())
        if user is None or not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentials
        return user, self._tokens.issue(user.id)

    def get_profile(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    def resolve_access_token(self, token: str) -> User | None:
        user_id = self._tokens.subject(token)
        return self._users.get(user_id) if user_id is not None else None

    def set_parental_pin(self, user_id: UUID, current_password: str, pin: str) -> User:
        user = self._users.get(user_id)
        if user is None or not self._password_hasher.verify(current_password, user.password_hash):
            raise InvalidCredentials
        user.parental_pin_hash = self._password_hasher.hash(pin)
        self._users.save(user)
        return user

    def validate_parental_pin(self, user_id: UUID, pin: str) -> bool:
        user = self._users.get(user_id)
        return bool(
            user is not None
            and user.parental_pin_hash is not None
            and self._password_hasher.verify(pin, user.parental_pin_hash)
        )
