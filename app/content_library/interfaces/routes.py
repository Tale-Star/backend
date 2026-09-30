"""Endpoints autenticados de referencias de biblioteca."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.content_library.application.service import ContentLibraryService
from app.content_library.domain.errors import LibraryItemAlreadySaved, LibraryResourceNotFound
from app.content_library.domain.models import LibraryItem, LibraryItemType
from app.content_library.interfaces.dependencies import get_content_library_service
from app.content_library.interfaces.schemas import (
    LibraryItemCreateRequest,
    LibraryItemPatchRequest,
    LibraryItemResponse,
)
from app.identity_access.domain.user import User
from app.identity_access.interfaces.dependencies import get_current_user
from app.shared.errors import ErrorResponse

router = APIRouter(
    prefix="/library",
    tags=["content-library"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required."},
        422: {"model": ErrorResponse, "description": "Request validation failed."},
    },
)


@router.post(
    "",
    response_model=LibraryItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found or not owned."},
        409: {"model": ErrorResponse, "description": "Resource already saved."},
    },
)
def create_library_item(
    request: LibraryItemCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
) -> LibraryItemResponse:
    try:
        item = service.create(
            user.id, request.type, request.resource_id, request.name, request.description
        )
    except LibraryResourceNotFound as error:
        raise _not_found("Library resource") from error
    except LibraryItemAlreadySaved as error:
        raise HTTPException(status_code=409, detail="Library resource already saved") from error
    return _response(item)


@router.get("", response_model=list[LibraryItemResponse])
def list_library_items(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
    item_type: Annotated[LibraryItemType | None, Query(alias="type")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    favorite: bool | None = None,
) -> list[LibraryItemResponse]:
    return [_response(item) for item in service.list(user.id, item_type, q, favorite)]


@router.get(
    "/{item_id}",
    response_model=LibraryItemResponse,
    responses={404: {"model": ErrorResponse, "description": "Library item not found."}},
)
def get_library_item(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
) -> LibraryItemResponse:
    item = service.get(item_id, user.id)
    if item is None:
        raise _not_found("Library item")
    return _response(item)


@router.patch(
    "/{item_id}",
    response_model=LibraryItemResponse,
    responses={404: {"model": ErrorResponse, "description": "Library item not found."}},
)
def patch_library_item(
    item_id: UUID,
    request: LibraryItemPatchRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
) -> LibraryItemResponse:
    item = service.get(item_id, user.id)
    if item is None:
        raise _not_found("Library item")
    for key, value in request.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(item, key, value)
    try:
        return _response(service.save(item))
    except LibraryResourceNotFound as error:
        raise _not_found("Library item") from error


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Library item not found."}},
)
def delete_library_item(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
) -> Response:
    if not service.delete(item_id, user.id):
        raise _not_found("Library item")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _response(item: LibraryItem) -> LibraryItemResponse:
    if item.item_type is LibraryItemType.STORY:
        resource_url = f"/api/v1/stories/{item.resource_id}"
    else:
        resource_url = f"/api/v1/media/assets/{item.resource_id}"
    return LibraryItemResponse(
        id=item.id,
        type=item.item_type,
        resource_id=item.resource_id,
        name=item.name,
        description=item.description,
        favorite=item.favorite,
        resource_url=resource_url,
        media_type=item.media_type,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} not found")
