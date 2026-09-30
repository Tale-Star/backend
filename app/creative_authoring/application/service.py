"""Casos de uso de CRUD creativo, stories y edición de páginas."""

from datetime import UTC, datetime
from uuid import UUID

from app.creative_authoring.application.ports import CreativeAuthoringRepository
from app.creative_authoring.domain.errors import CreativeResourceNotFound
from app.creative_authoring.domain.models import Character, Scenario, Story, StoryPage, StyleProfile


class CreativeAuthoringService:
    """Aplica ownership y referencias consistentes para contenido creativo."""

    def __init__(self, repository: CreativeAuthoringRepository) -> None:
        self._repository = repository

    def create_character(self, value: Character) -> Character:
        self._repository.add_character(value)
        return value

    def get_character(self, item_id: UUID, owner_id: UUID) -> Character | None:
        return self._repository.get_character(item_id, owner_id)

    def list_characters(self, owner_id: UUID, query: str | None = None) -> list[Character]:
        return self._repository.list_characters(owner_id, query)

    def save_character(self, value: Character) -> Character:
        self._require(self._repository.get_character(value.id, value.owner_id))
        value.updated_at = _utc_now()
        self._repository.save_character(value)
        return value

    def delete_character(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._repository.delete_character(item_id, owner_id)

    def create_scenario(self, value: Scenario) -> Scenario:
        self._repository.add_scenario(value)
        return value

    def get_scenario(self, item_id: UUID, owner_id: UUID) -> Scenario | None:
        return self._repository.get_scenario(item_id, owner_id)

    def list_scenarios(self, owner_id: UUID, query: str | None = None) -> list[Scenario]:
        return self._repository.list_scenarios(owner_id, query)

    def save_scenario(self, value: Scenario) -> Scenario:
        self._require(self._repository.get_scenario(value.id, value.owner_id))
        value.updated_at = _utc_now()
        self._repository.save_scenario(value)
        return value

    def delete_scenario(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._repository.delete_scenario(item_id, owner_id)

    def create_style_profile(self, value: StyleProfile) -> StyleProfile:
        self._repository.add_style_profile(value)
        return value

    def get_style_profile(self, item_id: UUID, owner_id: UUID) -> StyleProfile | None:
        return self._repository.get_style_profile(item_id, owner_id)

    def list_style_profiles(self, owner_id: UUID, query: str | None = None) -> list[StyleProfile]:
        return self._repository.list_style_profiles(owner_id, query)

    def save_style_profile(self, value: StyleProfile) -> StyleProfile:
        self._require(self._repository.get_style_profile(value.id, value.owner_id))
        value.updated_at = _utc_now()
        self._repository.save_style_profile(value)
        return value

    def delete_style_profile(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._repository.delete_style_profile(item_id, owner_id)

    def create_story(self, value: Story) -> Story:
        self._validate_story_references(value)
        self._repository.add_story(value)
        return value

    def get_story(self, item_id: UUID, owner_id: UUID) -> Story | None:
        return self._repository.get_story(item_id, owner_id)

    def list_stories(self, owner_id: UUID, query: str | None = None) -> list[Story]:
        return self._repository.list_stories(owner_id, query)

    def save_story(self, value: Story) -> Story:
        self._require(self._repository.get_story(value.id, value.owner_id))
        self._validate_story_references(value)
        value.updated_at = _utc_now()
        self._repository.save_story(value)
        return value

    def delete_story(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._repository.delete_story(item_id, owner_id)

    def create_page(self, value: StoryPage, owner_id: UUID) -> StoryPage:
        if self._repository.get_story(value.story_id, owner_id) is None:
            raise CreativeResourceNotFound
        self._validate_page_characters(value.character_ids, owner_id)
        self._repository.add_page(value)
        return value

    def get_page(self, page_id: UUID, story_id: UUID, owner_id: UUID) -> StoryPage | None:
        if self._repository.get_story(story_id, owner_id) is None:
            return None
        return self._repository.get_page(page_id, story_id, owner_id)

    def list_pages(self, story_id: UUID, owner_id: UUID) -> list[StoryPage] | None:
        if self._repository.get_story(story_id, owner_id) is None:
            return None
        return self._repository.list_pages(story_id, owner_id)

    def save_page(self, value: StoryPage, owner_id: UUID) -> StoryPage:
        self._require(self._repository.get_page(value.id, value.story_id, owner_id))
        self._validate_page_characters(value.character_ids, owner_id)
        value.updated_at = _utc_now()
        self._repository.save_page(value, owner_id)
        return value

    def delete_page(self, page_id: UUID, story_id: UUID, owner_id: UUID) -> bool:
        return self._repository.delete_page(page_id, story_id, owner_id)

    def _validate_story_references(self, story: Story) -> None:
        if (
            story.scenario_id is not None
            and self.get_scenario(story.scenario_id, story.owner_id) is None
        ):
            raise CreativeResourceNotFound
        if (
            story.style_profile_id is not None
            and self.get_style_profile(story.style_profile_id, story.owner_id) is None
        ):
            raise CreativeResourceNotFound

    def _validate_page_characters(self, character_ids: list[UUID], owner_id: UUID) -> None:
        if not self._repository.owns_characters(character_ids, owner_id):
            raise CreativeResourceNotFound

    @staticmethod
    def _require(value: object | None) -> None:
        if value is None:
            raise CreativeResourceNotFound


def _utc_now() -> datetime:
    return datetime.now(UTC)
