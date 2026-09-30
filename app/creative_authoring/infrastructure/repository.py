"""Adaptador SQLAlchemy para entidades de CreativeAuthoring."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.creative_authoring.application.ports import CreativeAuthoringRepository
from app.creative_authoring.domain.errors import DuplicatePageNumber
from app.creative_authoring.domain.models import Character, Scenario, Story, StoryPage, StyleProfile
from app.creative_authoring.infrastructure.models import (
    CharacterRecord,
    ScenarioRecord,
    StoryPageCharacterRecord,
    StoryPageRecord,
    StoryRecord,
    StyleProfileRecord,
)


class SqlAlchemyCreativeAuthoringRepository(CreativeAuthoringRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_character(self, value: Character) -> None:
        self._session.add(_character_record(value))
        self._commit()

    def get_character(self, item_id: UUID, owner_id: UUID) -> Character | None:
        row = _get_owned(self._session, CharacterRecord, item_id, owner_id)
        return _character(row) if row is not None else None

    def list_characters(self, owner_id: UUID, query: str | None = None) -> list[Character]:
        rows = _list_named(self._session, CharacterRecord, owner_id, query)
        return [_character(row) for row in rows]

    def save_character(self, value: Character) -> None:
        row = _get_owned(self._session, CharacterRecord, value.id, value.owner_id)
        if row is None:
            raise LookupError(f"Character {value.id} does not exist")
        row.name = value.name
        row.description = value.description
        row.visual_description = value.visual_description
        row.attributes = value.attributes
        row.updated_at = value.updated_at
        self._commit()

    def delete_character(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._delete_owned(CharacterRecord, item_id, owner_id)

    def add_scenario(self, value: Scenario) -> None:
        self._session.add(_scenario_record(value))
        self._commit()

    def get_scenario(self, item_id: UUID, owner_id: UUID) -> Scenario | None:
        row = _get_owned(self._session, ScenarioRecord, item_id, owner_id)
        return _scenario(row) if row is not None else None

    def list_scenarios(self, owner_id: UUID, query: str | None = None) -> list[Scenario]:
        rows = _list_named(self._session, ScenarioRecord, owner_id, query)
        return [_scenario(row) for row in rows]

    def save_scenario(self, value: Scenario) -> None:
        row = _get_owned(self._session, ScenarioRecord, value.id, value.owner_id)
        if row is None:
            raise LookupError(f"Scenario {value.id} does not exist")
        row.name = value.name
        row.description = value.description
        row.visual_description = value.visual_description
        row.seed = value.seed
        row.updated_at = value.updated_at
        self._commit()

    def delete_scenario(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._delete_owned(ScenarioRecord, item_id, owner_id)

    def add_style_profile(self, value: StyleProfile) -> None:
        self._session.add(_style_record(value))
        self._commit()

    def get_style_profile(self, item_id: UUID, owner_id: UUID) -> StyleProfile | None:
        row = _get_owned(self._session, StyleProfileRecord, item_id, owner_id)
        return _style(row) if row is not None else None

    def list_style_profiles(self, owner_id: UUID, query: str | None = None) -> list[StyleProfile]:
        rows = _list_named(self._session, StyleProfileRecord, owner_id, query)
        return [_style(row) for row in rows]

    def save_style_profile(self, value: StyleProfile) -> None:
        row = _get_owned(self._session, StyleProfileRecord, value.id, value.owner_id)
        if row is None:
            raise LookupError(f"StyleProfile {value.id} does not exist")
        row.name = value.name
        row.description = value.description
        row.prompt_modifier = value.prompt_modifier
        row.visual_settings = value.visual_settings
        row.updated_at = value.updated_at
        self._commit()

    def delete_style_profile(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._delete_owned(StyleProfileRecord, item_id, owner_id)

    def add_story(self, value: Story) -> None:
        self._session.add(_story_record(value))
        self._commit()

    def get_story(self, item_id: UUID, owner_id: UUID) -> Story | None:
        row = _get_owned(self._session, StoryRecord, item_id, owner_id)
        return _story(row) if row is not None else None

    def list_stories(self, owner_id: UUID, query: str | None = None) -> list[Story]:
        rows = _list_named(self._session, StoryRecord, owner_id, query)
        return [_story(row) for row in rows]

    def save_story(self, value: Story) -> None:
        row = _get_owned(self._session, StoryRecord, value.id, value.owner_id)
        if row is None:
            raise LookupError(f"Story {value.id} does not exist")
        row.title = value.title
        row.description = value.description
        row.scenario_id = value.scenario_id
        row.style_profile_id = value.style_profile_id
        row.seed = value.seed
        row.updated_at = value.updated_at
        self._commit()

    def delete_story(self, item_id: UUID, owner_id: UUID) -> bool:
        return self._delete_owned(StoryRecord, item_id, owner_id)

    def add_page(self, value: StoryPage) -> None:
        self._session.add(_page_record(value))
        try:
            # Persist the page first because this adapter intentionally models the
            # association table without ORM relationships.
            self._session.flush()
        except IntegrityError as error:
            self._session.rollback()
            _raise_page_integrity(error)
        self._replace_page_characters(value.id, value.character_ids)
        self._commit_page()

    def get_page(self, page_id: UUID, story_id: UUID, owner_id: UUID) -> StoryPage | None:
        row = self._owned_page_query(page_id, story_id, owner_id).first()
        return self._page(row) if row is not None else None

    def list_pages(self, story_id: UUID, owner_id: UUID) -> list[StoryPage]:
        rows = self._session.scalars(
            select(StoryPageRecord)
            .join(StoryRecord, StoryRecord.id == StoryPageRecord.story_id)
            .where(StoryPageRecord.story_id == story_id, StoryRecord.owner_id == owner_id)
            .order_by(StoryPageRecord.page_number)
        ).all()
        if not rows:
            return []
        positions = self._character_positions([row.id for row in rows])
        return [self._page(row, positions[row.id]) for row in rows]

    def save_page(self, value: StoryPage, owner_id: UUID) -> None:
        row = self._owned_page_query(value.id, value.story_id, owner_id).first()
        if row is None:
            raise LookupError(f"StoryPage {value.id} does not exist")
        row.page_number = value.page_number
        row.action = value.action
        row.text = value.text
        row.visual_config = value.visual_config
        row.seed = value.seed
        row.updated_at = value.updated_at
        self._session.execute(
            delete(StoryPageCharacterRecord).where(StoryPageCharacterRecord.page_id == value.id)
        )
        self._replace_page_characters(value.id, value.character_ids)
        self._commit_page()

    def delete_page(self, page_id: UUID, story_id: UUID, owner_id: UUID) -> bool:
        row = self._owned_page_query(page_id, story_id, owner_id).first()
        if row is None:
            return False
        self._session.delete(row)
        self._commit()
        return True

    def owns_characters(self, character_ids: list[UUID], owner_id: UUID) -> bool:
        unique_ids = set(character_ids)
        if not unique_ids:
            return True
        count = self._session.scalar(
            select(func.count(CharacterRecord.id)).where(
                CharacterRecord.owner_id == owner_id,
                CharacterRecord.id.in_(unique_ids),
            )
        )
        return count == len(unique_ids)

    def _delete_owned(self, model: Any, item_id: UUID, owner_id: UUID) -> bool:
        row = _get_owned(self._session, model, item_id, owner_id)
        if row is None:
            return False
        self._session.delete(row)
        self._commit()
        return True

    def _owned_page_query(self, page_id: UUID, story_id: UUID, owner_id: UUID) -> Any:
        statement = (
            select(StoryPageRecord)
            .join(StoryRecord, StoryRecord.id == StoryPageRecord.story_id)
            .where(
                StoryPageRecord.id == page_id,
                StoryPageRecord.story_id == story_id,
                StoryRecord.owner_id == owner_id,
            )
        )
        return self._session.scalars(statement)

    def _replace_page_characters(self, page_id: UUID, character_ids: list[UUID]) -> None:
        for position, character_id in enumerate(dict.fromkeys(character_ids)):
            self._session.add(
                StoryPageCharacterRecord(
                    page_id=page_id, character_id=character_id, position=position
                )
            )

    def _character_positions(self, page_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        result: dict[UUID, list[UUID]] = {page_id: [] for page_id in page_ids}
        rows = self._session.scalars(
            select(StoryPageCharacterRecord)
            .where(StoryPageCharacterRecord.page_id.in_(page_ids))
            .order_by(StoryPageCharacterRecord.position)
        ).all()
        for row in rows:
            result[row.page_id].append(row.character_id)
        return result

    def _page(self, row: StoryPageRecord, character_ids: list[UUID] | None = None) -> StoryPage:
        if character_ids is None:
            character_ids = self._character_positions([row.id])[row.id]
        return StoryPage(
            id=row.id,
            story_id=row.story_id,
            page_number=row.page_number,
            action=row.action,
            text=row.text,
            visual_config=row.visual_config,
            seed=row.seed,
            character_ids=character_ids,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _commit_page(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            _raise_page_integrity(error)
        except Exception:
            self._session.rollback()
            raise

    def _commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise


def _raise_page_integrity(error: IntegrityError) -> None:
    if "creative_story_pages.story_id, creative_story_pages.page_number" in str(error):
        raise DuplicatePageNumber from error
    raise error


def _get_owned(session: Session, model: Any, item_id: UUID, owner_id: UUID) -> Any | None:
    return session.scalar(select(model).where(model.id == item_id, model.owner_id == owner_id))


def _list_named(session: Session, model: Any, owner_id: UUID, query: str | None) -> list[Any]:
    statement: Any = select(model).where(model.owner_id == owner_id)
    if query:
        pattern = f"%{query.strip().casefold()}%"
        if hasattr(model, "title"):
            statement = statement.where(func.lower(model.title).like(pattern))
        else:
            statement = statement.where(func.lower(model.name).like(pattern))
    order_field = model.title if hasattr(model, "title") else model.name
    return list(session.scalars(statement.order_by(func.lower(order_field), model.id)).all())


def _character_record(value: Character) -> CharacterRecord:
    return CharacterRecord(
        id=value.id,
        owner_id=value.owner_id,
        name=value.name,
        description=value.description,
        visual_description=value.visual_description,
        attributes=value.attributes,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def _character(row: CharacterRecord) -> Character:
    return Character(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description,
        visual_description=row.visual_description,
        attributes=row.attributes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _scenario_record(value: Scenario) -> ScenarioRecord:
    return ScenarioRecord(
        id=value.id,
        owner_id=value.owner_id,
        name=value.name,
        description=value.description,
        visual_description=value.visual_description,
        seed=value.seed,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def _scenario(row: ScenarioRecord) -> Scenario:
    return Scenario(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description,
        visual_description=row.visual_description,
        seed=row.seed,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _style_record(value: StyleProfile) -> StyleProfileRecord:
    return StyleProfileRecord(
        id=value.id,
        owner_id=value.owner_id,
        name=value.name,
        description=value.description,
        prompt_modifier=value.prompt_modifier,
        visual_settings=value.visual_settings,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def _style(row: StyleProfileRecord) -> StyleProfile:
    return StyleProfile(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description,
        prompt_modifier=row.prompt_modifier,
        visual_settings=row.visual_settings,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _story_record(value: Story) -> StoryRecord:
    return StoryRecord(
        id=value.id,
        owner_id=value.owner_id,
        title=value.title,
        description=value.description,
        scenario_id=value.scenario_id,
        style_profile_id=value.style_profile_id,
        seed=value.seed,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def _story(row: StoryRecord) -> Story:
    return Story(
        id=row.id,
        owner_id=row.owner_id,
        title=row.title,
        description=row.description,
        scenario_id=row.scenario_id,
        style_profile_id=row.style_profile_id,
        seed=row.seed,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _page_record(value: StoryPage) -> StoryPageRecord:
    return StoryPageRecord(
        id=value.id,
        story_id=value.story_id,
        page_number=value.page_number,
        action=value.action,
        text=value.text,
        visual_config=value.visual_config,
        seed=value.seed,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )
