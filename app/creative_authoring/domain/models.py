"""Entidades del módulo CreativeAuthoring, sin dependencias de infraestructura."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.shared.domain.entity import Entity


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False, slots=True)
class Character(Entity):
    owner_id: UUID
    name: str
    description: str = ""
    visual_description: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(eq=False, slots=True)
class Scenario(Entity):
    owner_id: UUID
    name: str
    description: str = ""
    visual_description: str = ""
    seed: int | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(eq=False, slots=True)
class StyleProfile(Entity):
    owner_id: UUID
    name: str
    description: str = ""
    prompt_modifier: str = ""
    visual_settings: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(eq=False, slots=True)
class Story(Entity):
    owner_id: UUID
    title: str
    description: str = ""
    scenario_id: UUID | None = None
    style_profile_id: UUID | None = None
    seed: int | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(eq=False, slots=True)
class StoryPage(Entity):
    story_id: UUID
    page_number: int
    action: str = ""
    text: str = ""
    visual_config: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    character_ids: list[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
