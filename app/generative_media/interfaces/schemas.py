"""HTTP request and response schemas for GenerativeMedia."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.generative_media.domain.generation_job import GenerationStatus, GenerationType

MAX_SEED = 4_294_967_295


class ImageGenerationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    action: str = Field(default="", max_length=200, alias="Action")
    emotion: str = Field(default="", max_length=200, alias="Emotion")
    scene: str = Field(default="", max_length=500, alias="Scene")
    moment: str = Field(default="", max_length=500, alias="Moment")
    extra: str = Field(default="", max_length=2000, alias="Extra")
    free_prompt: str = Field(default="", max_length=4000, alias="FreePrompt")
    style: str = Field(default="", max_length=200, alias="Style")
    characters: list[str] = Field(default_factory=list, max_length=50, alias="Characters")
    objects: list[str] = Field(default_factory=list, max_length=50, alias="Objects")
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED, alias="Seed")


class MusicSectionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    type: str = Field(default="", max_length=100, alias="Type")
    modifier: str = Field(default="", max_length=300, alias="Modifier")
    text: str = Field(default="", max_length=2000, alias="Text")


class MusicGenerationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    caption: str = Field(default="", max_length=4000, alias="Caption")
    duration: int = Field(ge=10, le=600, alias="Duration")
    bpm: int = Field(ge=30, le=300, alias="Bpm")
    voice: str = Field(default="", max_length=100, alias="Voice")
    language: Literal["Español", "English"] = Field(alias="Language")
    output: Literal["song", "instrumental"] = Field(alias="Output")
    genre: list[str] = Field(default_factory=list, max_length=50, alias="Genre")
    mood: list[str] = Field(default_factory=list, max_length=50, alias="Mood")
    instruments: list[str] = Field(default_factory=list, max_length=50, alias="Instruments")
    production: list[str] = Field(default_factory=list, max_length=50, alias="Production")
    sections: list[MusicSectionRequest] = Field(
        default_factory=list, max_length=50, alias="Sections"
    )
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED, alias="Seed")


class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: GenerationType
    status: GenerationStatus
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error_message: str | None
    seed: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    attempts: int
