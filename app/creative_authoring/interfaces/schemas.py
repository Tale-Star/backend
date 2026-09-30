"""Schemas de API para personajes, escenarios, estilos e historias."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_SEED = 4_294_967_295
CharacterName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
ScenarioName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
ProfileName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
StoryTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class CharacterCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CharacterName
    description: str = Field(default="", max_length=5000)
    visual_description: str = Field(default="", max_length=4000)
    attributes: dict[str, Any] = Field(default_factory=dict)


class CharacterPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CharacterName | None = None
    description: str | None = Field(default=None, max_length=5000)
    visual_description: str | None = Field(default=None, max_length=4000)
    attributes: dict[str, Any] | None = None


class CharacterResponse(BaseModel):
    id: UUID
    name: str
    description: str
    visual_description: str
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ScenarioCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ScenarioName
    description: str = Field(default="", max_length=5000)
    visual_description: str = Field(default="", max_length=4000)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)


class ScenarioPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ScenarioName | None = None
    description: str | None = Field(default=None, max_length=5000)
    visual_description: str | None = Field(default=None, max_length=4000)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)


class ScenarioResponse(BaseModel):
    id: UUID
    name: str
    description: str
    visual_description: str
    seed: int | None
    created_at: datetime
    updated_at: datetime


class StyleProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProfileName
    description: str = Field(default="", max_length=3000)
    prompt_modifier: str = Field(default="", max_length=4000)
    visual_settings: dict[str, Any] = Field(default_factory=dict)


class StyleProfilePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProfileName | None = None
    description: str | None = Field(default=None, max_length=3000)
    prompt_modifier: str | None = Field(default=None, max_length=4000)
    visual_settings: dict[str, Any] | None = None


class StyleProfileResponse(BaseModel):
    id: UUID
    name: str
    description: str
    prompt_modifier: str
    visual_settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class StoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: StoryTitle
    description: str = Field(default="", max_length=10000)
    scenario_id: UUID | None = None
    style_profile_id: UUID | None = None
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)


class StoryPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: StoryTitle | None = None
    description: str | None = Field(default=None, max_length=10000)
    scenario_id: UUID | None = None
    style_profile_id: UUID | None = None
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)


class StoryResponse(BaseModel):
    id: UUID
    title: str
    description: str
    scenario_id: UUID | None
    style_profile_id: UUID | None
    seed: int | None
    created_at: datetime
    updated_at: datetime


class StoryPageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1, le=1000)
    action: str = Field(default="", max_length=2000)
    text: str = Field(default="", max_length=20000)
    visual_config: dict[str, Any] = Field(default_factory=dict)
    character_ids: list[UUID] = Field(default_factory=list, max_length=50)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)


class StoryPagePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int | None = Field(default=None, ge=1, le=1000)
    action: str | None = Field(default=None, max_length=2000)
    text: str | None = Field(default=None, max_length=20000)
    visual_config: dict[str, Any] | None = None
    character_ids: list[UUID] | None = Field(default=None, max_length=50)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)


class StoryPageResponse(BaseModel):
    id: UUID
    story_id: UUID
    page_number: int
    action: str
    text: str
    visual_config: dict[str, Any]
    character_ids: list[UUID]
    seed: int | None
    created_at: datetime
    updated_at: datetime
