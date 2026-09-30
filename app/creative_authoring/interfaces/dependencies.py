"""Dependencias HTTP de CreativeAuthoring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.creative_authoring.application.service import CreativeAuthoringService
from app.creative_authoring.infrastructure.repository import SqlAlchemyCreativeAuthoringRepository
from app.shared.database.session import get_db_session


def get_creative_authoring_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CreativeAuthoringService:
    return CreativeAuthoringService(SqlAlchemyCreativeAuthoringRepository(session))
