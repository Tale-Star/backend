"""Adapters de hashing Argon2id y JWT HS256."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.identity_access.application.ports import AccessTokenPort, PasswordHasherPort
from app.shared.config.settings import Settings


class Argon2PasswordHasher(PasswordHasherPort):
    """Hash seguro para contraseñas y PIN con el algoritmo recomendado por pwdlib."""

    def __init__(self) -> None:
        self._hasher = PasswordHash.recommended()

    def hash(self, value: str) -> str:
        return self._hasher.hash(value)

    def verify(self, value: str, encoded_hash: str) -> bool:
        try:
            return self._hasher.verify(value, encoded_hash)
        except (ValueError, TypeError):
            return False


class JwtAccessTokenAdapter(AccessTokenPort):
    """Emite y valida JWT access tokens breves con HS256."""

    _issuer = "tale-star-api"
    _algorithm = "HS256"

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret_key.get_secret_value()
        self._expires = timedelta(minutes=settings.jwt_access_token_minutes)

    def issue(self, subject: UUID) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(subject),
                "iat": now,
                "exp": now + self._expires,
                "iss": self._issuer,
            },
            self._secret,
            algorithm=self._algorithm,
        )

    def subject(self, token: str) -> UUID | None:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={"require": ["sub", "iat", "exp", "iss"]},
            )
            return UUID(payload["sub"])
        except (InvalidTokenError, ValueError, TypeError, KeyError):
            return None
