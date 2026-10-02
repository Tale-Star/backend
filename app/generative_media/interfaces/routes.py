"""Rutas HTTP de jobs de generación y assets."""

import mimetypes
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import Annotated, BinaryIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.creative_authoring.application.service import CreativeAuthoringService
from app.creative_authoring.interfaces.dependencies import get_creative_authoring_service
from app.generative_media.application.asset_storage import AssetStorage
from app.generative_media.application.generation_service import GenerationJobService
from app.generative_media.domain.generation_job import GenerationType
from app.generative_media.infrastructure.character_prompt import enrich_image_payload
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
    tags=["Generative Media"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required."},
        422: {"model": ErrorResponse, "description": "Request validation failed."},
    },
)
media_router = APIRouter(
    prefix="/media",
    tags=["Media"],
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
) -> StreamingResponse:
    """Resuelve un identificador de asset propio sin exponer su ruta de filesystem."""
    asset = service.get_asset(asset_id, user.id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Media asset not found")
    storage: AssetStorage = request.app.state.asset_storage
    try:
        asset_file = storage.open_key(asset.path, user.id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Media asset not found") from None
    return StreamingResponse(
        _iter_asset(asset_file),
        media_type=_media_type_for(PurePosixPath(asset.path).name, asset.media_type),
        headers={"X-Content-Type-Options": "nosniff"},
    )


@media_router.get("/{asset_key:path}")
def get_media(
    asset_key: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Sirve una clave propia sin revelar su ubicación de almacenamiento."""
    storage: AssetStorage = request.app.state.asset_storage
    try:
        asset_file = storage.open_key(asset_key, user.id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Media asset not found") from None
    return StreamingResponse(
        _iter_asset(asset_file),
        media_type=_media_type_for(PurePosixPath(asset_key).name),
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("/images", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_image_generation(
    request: ImageGenerationRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationJobService, Depends(get_generation_job_service)],
    authoring: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> GenerationJobResponse:
    """Persiste una solicitud de imagen sin ejecutar generación en el API."""
    payload = enrich_image_payload(
        request.model_dump(by_alias=True), authoring.list_characters(user.id)
    )
    style_name = request.style.strip().casefold()
    if style_name:
        style = next(
            (
                profile
                for profile in authoring.list_style_profiles(user.id)
                if profile.name.strip().casefold() == style_name
            ),
            None,
        )
        if style is not None:
            payload["StyleProfileDetails"] = {
                "prompt_modifier": style.prompt_modifier,
                "visual_settings": style.visual_settings,
            }
    job = service.create(
        GenerationType.IMAGE,
        payload,
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


def _media_type_for(filename: str, stored_media_type: str | None = None) -> str:
    """Prefer the trusted media type recorded with an asset over OS MIME guesses."""
    if stored_media_type:
        return stored_media_type
    if filename.lower().endswith(".flac"):
        return "audio/flac"
    media_type, _encoding = mimetypes.guess_type(filename)
    return media_type or "application/octet-stream"


def _iter_asset(asset_file: BinaryIO) -> Iterator[bytes]:
    """Transmite un asset por chunks y cierra el stream al terminar o cancelar."""
    try:
        while chunk := asset_file.read(64 * 1024):
            yield chunk
    finally:
        asset_file.close()
