"""Dependencias HTTP de IdentityAccess."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.identity_access.application.service import IdentityAccessService
from app.identity_access.domain.user import User
from app.identity_access.infrastructure.security import Argon2PasswordHasher, JwtAccessTokenAdapter
from app.identity_access.infrastructure.user_repository import SqlAlchemyUserRepository
from app.shared.config.settings import Settings
from app.shared.database.session import get_db_session

bearer_scheme = HTTPBearer(auto_error=False)


def _get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_identity_access_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(_get_settings)],
) -> IdentityAccessService:
    return IdentityAccessService(
        SqlAlchemyUserRepository(session), Argon2PasswordHasher(), JwtAccessTokenAdapter(settings)
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[IdentityAccessService, Depends(get_identity_access_service)],
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = service.resolve_access_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
