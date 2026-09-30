"""Rutas HTTP de jobs de generación y assets locales."""

import mimetypes
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.generative_media.application.generation_service import GenerationJobService
from app.generative_media.domain.generation_job import GenerationType
from app.generative_media.infrastructure.local_asset_storage import LocalAssetStorage
from app.generative_media.interfaces.dependencies import get_generation_job_service
from app.generative_media.interfaces.schemas import (
    GenerationJobResponse,
    ImageGenerationRequest,
    MusicGenerationRequest,
)
from app.identity_access.domain.user import User
from app.identity_access.interfaces.dependencies import get_current_user
from app.shared.errors import ErrorResponse

router = APIRouter(
    prefix="/generations",
    tags=["generations"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required."},
        422: {"model": ErrorResponse, "description": "Request validation failed."},
    },
)
media_router = APIRouter(
    prefix="/media",
    tags=["media"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required."},
        404: {"model": ErrorResponse, "description": "Asset not found."},
    },
)


@media_router.get(
    "/assets/{asset_id}",
    responses={404: {"model": ErrorResponse, "description": "Asset not found or not owned."}},
)
def get_media_by_id(
    asset_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationJobService, Depends(get_generation_job_service)],
) -> FileResponse:
    """Resuelve un identificador de asset propio sin exponer su ruta de filesystem."""
    asset = service.get_asset(asset_id, user.id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Media asset not found")
    storage: LocalAssetStorage = request.app.state.media_storage
    try:
        path = storage.resolve_key(asset.path, user.id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Media asset not found") from None
    media_type, _encoding = mimetypes.guess_type(path.name)
    return FileResponse(
        path,
        media_type=media_type or asset.media_type or "application/octet-stream",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@media_router.get("/{asset_key:path}")
def get_media(
    asset_key: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Sirve únicamente archivos dentro del directorio local de medios."""
    storage: LocalAssetStorage = request.app.state.media_storage
    try:
        path = storage.resolve_key(asset_key, user.id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Media asset not found") from None
    media_type, _encoding = mimetypes.guess_type(path.name)
    return FileResponse(
        path,
        media_type=media_type or "application/octet-stream",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("/images", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_image_generation(
    request: ImageGenerationRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationJobService, Depends(get_generation_job_service)],
) -> GenerationJobResponse:
    """Persiste una solicitud de imagen sin ejecutar generación en el API."""
    job = service.create(
        GenerationType.IMAGE,
        request.model_dump(by_alias=True),
        request.seed,
        user.id,
    )
    return GenerationJobResponse.model_validate(job)


@router.post("/music", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_music_generation(
    request: MusicGenerationRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationJobService, Depends(get_generation_job_service)],
) -> GenerationJobResponse:
    """Persiste una solicitud musical sin ejecutar generación en el API."""
    job = service.create(
        GenerationType.MUSIC,
        request.model_dump(by_alias=True),
        request.seed,
        user.id,
    )
    return GenerationJobResponse.model_validate(job)


@router.get(
    "/{job_id}",
    response_model=GenerationJobResponse,
    responses={404: {"model": ErrorResponse, "description": "Job not found."}},
)
def get_generation(
    job_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationJobService, Depends(get_generation_job_service)],
) -> GenerationJobResponse:
    """Devuelve el estado persistido o 404 si el ID no existe."""
    job = service.get(job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return GenerationJobResponse.model_validate(job)
