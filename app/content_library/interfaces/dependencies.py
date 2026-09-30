"""Dependencias de aplicación para ContentLibrary."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.content_library.application.service import ContentLibraryService
from app.content_library.infrastructure.repository import SqlAlchemyLibraryRepository
from app.content_library.infrastructure.resource_resolver import SqlAlchemyLibraryResourceResolver
from app.shared.database.session import get_db_session


def get_content_library_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ContentLibraryService:
    return ContentLibraryService(
        SqlAlchemyLibraryRepository(session), SqlAlchemyLibraryResourceResolver(session)
    )
