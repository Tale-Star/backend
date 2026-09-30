"""Endpoints CRUD de contenido reutilizable e historias editables por páginas."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.creative_authoring.application.service import CreativeAuthoringService
from app.creative_authoring.domain.errors import CreativeResourceNotFound, DuplicatePageNumber
from app.creative_authoring.domain.models import Character, Scenario, Story, StoryPage, StyleProfile
from app.creative_authoring.interfaces.dependencies import get_creative_authoring_service
from app.creative_authoring.interfaces.schemas import (
    CharacterCreateRequest,
    CharacterPatchRequest,
    CharacterResponse,
    ScenarioCreateRequest,
    ScenarioPatchRequest,
    ScenarioResponse,
    StoryCreateRequest,
    StoryPageCreateRequest,
    StoryPagePatchRequest,
    StoryPageResponse,
    StoryPatchRequest,
    StoryResponse,
    StyleProfileCreateRequest,
    StyleProfilePatchRequest,
    StyleProfileResponse,
)
from app.identity_access.domain.user import User
from app.identity_access.interfaces.dependencies import get_current_user
from app.shared.errors import AppError, ErrorResponse

router = APIRouter(
    tags=["Creative Authoring"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required."},
        422: {"model": ErrorResponse, "description": "Request validation failed."},
    },
)


@router.post("/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
def create_character(
    request: CharacterCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Character:
    return service.create_character(Character(owner_id=user.id, **request.model_dump()))


@router.get("/characters", response_model=list[CharacterResponse])
def list_characters(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> list[Character]:
    return service.list_characters(user.id, q)


@router.get(
    "/characters/{item_id}",
    response_model=CharacterResponse,
    responses={404: {"model": ErrorResponse, "description": "Character not found."}},
)
def get_character(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Character:
    value = service.get_character(item_id, user.id)
    if value is None:
        raise _not_found("Character")
    return value


@router.patch(
    "/characters/{item_id}",
    response_model=CharacterResponse,
    responses={404: {"model": ErrorResponse, "description": "Character not found."}},
)
def patch_character(
    item_id: UUID,
    request: CharacterPatchRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Character:
    value = service.get_character(item_id, user.id)
    if value is None:
        raise _not_found("Character")
    _apply_patch(value, request.model_dump(exclude_unset=True))
    try:
        return service.save_character(value)
    except CreativeResourceNotFound as error:
        raise _not_found("Character") from error


@router.delete(
    "/characters/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Character not found."}},
)
def delete_character(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Response:
    if not service.delete_character(item_id, user.id):
        raise _not_found("Character")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/scenarios", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    request: ScenarioCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Scenario:
    return service.create_scenario(Scenario(owner_id=user.id, **request.model_dump()))


@router.get("/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> list[Scenario]:
    return service.list_scenarios(user.id, q)


@router.get(
    "/scenarios/{item_id}",
    response_model=ScenarioResponse,
    responses={404: {"model": ErrorResponse, "description": "Scenario not found."}},
)
def get_scenario(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Scenario:
    value = service.get_scenario(item_id, user.id)
    if value is None:
        raise _not_found("Scenario")
    return value


@router.patch(
    "/scenarios/{item_id}",
    response_model=ScenarioResponse,
    responses={404: {"model": ErrorResponse, "description": "Scenario not found."}},
)
def patch_scenario(
    item_id: UUID,
    request: ScenarioPatchRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Scenario:
    value = service.get_scenario(item_id, user.id)
    if value is None:
        raise _not_found("Scenario")
    _apply_patch(value, request.model_dump(exclude_unset=True), nullable={"seed"})
    return service.save_scenario(value)


@router.delete(
    "/scenarios/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Scenario not found."}},
)
def delete_scenario(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Response:
    if not service.delete_scenario(item_id, user.id):
        raise _not_found("Scenario")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/style-profiles", response_model=StyleProfileResponse, status_code=status.HTTP_201_CREATED
)
def create_style_profile(
    request: StyleProfileCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> StyleProfile:
    return service.create_style_profile(StyleProfile(owner_id=user.id, **request.model_dump()))


@router.get("/style-profiles", response_model=list[StyleProfileResponse])
def list_style_profiles(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> list[StyleProfile]:
    return service.list_style_profiles(user.id, q)


@router.get(
    "/style-profiles/{item_id}",
    response_model=StyleProfileResponse,
    responses={404: {"model": ErrorResponse, "description": "Style profile not found."}},
)
def get_style_profile(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> StyleProfile:
    value = service.get_style_profile(item_id, user.id)
    if value is None:
        raise _not_found("StyleProfile")
    return value


@router.patch(
    "/style-profiles/{item_id}",
    response_model=StyleProfileResponse,
    responses={404: {"model": ErrorResponse, "description": "Style profile not found."}},
)
def patch_style_profile(
    item_id: UUID,
    request: StyleProfilePatchRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> StyleProfile:
    value = service.get_style_profile(item_id, user.id)
    if value is None:
        raise _not_found("StyleProfile")
    _apply_patch(value, request.model_dump(exclude_unset=True))
    return service.save_style_profile(value)


@router.delete(
    "/style-profiles/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Style profile not found."}},
)
def delete_style_profile(
    item_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Response:
    if not service.delete_style_profile(item_id, user.id):
        raise _not_found("StyleProfile")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/stories",
    response_model=StoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse, "description": "Scenario or style profile not found."}
    },
)
def create_story(
    request: StoryCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Story:
    try:
        return service.create_story(Story(owner_id=user.id, **request.model_dump()))
    except CreativeResourceNotFound as error:
        raise _not_found("Scenario or StyleProfile") from error


@router.get("/stories", response_model=list[StoryResponse])
def list_stories(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> list[Story]:
    return service.list_stories(user.id, q)


@router.get(
    "/stories/{story_id}",
    response_model=StoryResponse,
    responses={404: {"model": ErrorResponse, "description": "Story not found."}},
)
def get_story(
    story_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Story:
    value = service.get_story(story_id, user.id)
    if value is None:
        raise _not_found("Story")
    return value


@router.patch(
    "/stories/{story_id}",
    response_model=StoryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Story or referenced resource not found."}
    },
)
def patch_story(
    story_id: UUID,
    request: StoryPatchRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Story:
    value = service.get_story(story_id, user.id)
    if value is None:
        raise _not_found("Story")
    _apply_patch(
        value,
        request.model_dump(exclude_unset=True),
        nullable={"scenario_id", "style_profile_id", "seed"},
    )
    try:
        return service.save_story(value)
    except CreativeResourceNotFound as error:
        raise _not_found("Scenario, StyleProfile or Story") from error


@router.delete(
    "/stories/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Story not found."}},
)
def delete_story(
    story_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Response:
    if not service.delete_story(story_id, user.id):
        raise _not_found("Story")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/stories/{story_id}/pages",
    response_model=StoryPageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse, "description": "Story or character not found."},
        409: {"model": ErrorResponse, "description": "Page number already exists."},
    },
)
def create_story_page(
    story_id: UUID,
    request: StoryPageCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> StoryPage:
    value = StoryPage(story_id=story_id, **request.model_dump())
    try:
        return service.create_page(value, user.id)
    except CreativeResourceNotFound as error:
        raise _not_found("Story or Character") from error
    except DuplicatePageNumber as error:
        raise AppError(
            "Page number already exists", code="duplicate_page_number", status_code=409
        ) from error


@router.get(
    "/stories/{story_id}/pages",
    response_model=list[StoryPageResponse],
    responses={404: {"model": ErrorResponse, "description": "Story not found."}},
)
def list_story_pages(
    story_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> list[StoryPage]:
    pages = service.list_pages(story_id, user.id)
    if pages is None:
        raise _not_found("Story")
    return pages


@router.get(
    "/stories/{story_id}/pages/{page_id}",
    response_model=StoryPageResponse,
    responses={404: {"model": ErrorResponse, "description": "Story page not found."}},
)
def get_story_page(
    story_id: UUID,
    page_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> StoryPage:
    value = service.get_page(page_id, story_id, user.id)
    if value is None:
        raise _not_found("StoryPage")
    return value


@router.patch(
    "/stories/{story_id}/pages/{page_id}",
    response_model=StoryPageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Story, page or character not found."},
        409: {"model": ErrorResponse, "description": "Page number already exists."},
    },
)
def patch_story_page(
    story_id: UUID,
    page_id: UUID,
    request: StoryPagePatchRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> StoryPage:
    value = service.get_page(page_id, story_id, user.id)
    if value is None:
        raise _not_found("StoryPage")
    _apply_patch(value, request.model_dump(exclude_unset=True), nullable={"seed"})
    try:
        return service.save_page(value, user.id)
    except CreativeResourceNotFound as error:
        raise _not_found("Story or Character") from error
    except DuplicatePageNumber as error:
        raise AppError(
            "Page number already exists", code="duplicate_page_number", status_code=409
        ) from error


@router.delete(
    "/stories/{story_id}/pages/{page_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Story page not found."}},
)
def delete_story_page(
    story_id: UUID,
    page_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreativeAuthoringService, Depends(get_creative_authoring_service)],
) -> Response:
    if not service.delete_page(page_id, story_id, user.id):
        raise _not_found("StoryPage")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _apply_patch(
    value: object, fields: dict[str, object], nullable: set[str] | None = None
) -> None:
    allowed_nullable = nullable or set()
    for field_name, field_value in fields.items():
        if field_value is not None or field_name in allowed_nullable:
            setattr(value, field_name, field_value)


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} not found")
