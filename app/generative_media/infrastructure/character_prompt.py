"""Resolves owned characters and expands @mentions before a generation is queued."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any

from app.creative_authoring.domain.models import Character

TEXT_FIELDS = ("Action", "Emotion", "Scene", "Moment", "Extra", "FreePrompt")


def enrich_image_payload(
    payload: dict[str, Any], characters: Iterable[Character]
) -> dict[str, Any]:
    """Replaces known @names with descriptions and records descriptions for selected names."""
    rows = list(characters)
    by_name = {row.name.strip().casefold(): row for row in rows if row.name.strip()}
    selected_names = payload.get("Characters", [])
    if not isinstance(selected_names, list):
        selected_names = []
    requested: list[str] = []
    requested_keys: set[str] = set()

    def request_name(name: str) -> None:
        normalized = name.strip().casefold()
        if normalized and normalized not in requested_keys:
            requested.append(normalized)
            requested_keys.add(normalized)

    for name in selected_names:
        if isinstance(name, str):
            request_name(name)

    text_values = [payload.get(field, "") for field in TEXT_FIELDS]
    for value in text_values:
        if not isinstance(value, str):
            continue
        for character in rows:
            name = character.name.strip()
            if name and re.search(rf"(?<!\w)@{re.escape(name)}(?!\w)", value, re.IGNORECASE):
                request_name(name)

    selected = [by_name[name] for name in requested if name in by_name]
    descriptions = {
        row.name.strip().casefold(): _character_tags(row)
        for row in selected
        if _character_tags(row)
    }

    expanded = dict(payload)
    for field in TEXT_FIELDS:
        value = expanded.get(field)
        if not isinstance(value, str) or "@" not in value:
            continue
        for row in sorted(rows, key=lambda item: len(item.name), reverse=True):
            name = row.name.strip()
            description = descriptions.get(name.casefold())
            if name and description is not None:
                value = re.sub(
                    rf"(?<!\w)@{re.escape(name)}(?!\w)",
                    _constant_replacer(description),
                    value,
                    flags=re.IGNORECASE,
                )
        expanded[field] = value

    expanded["CharacterDescriptions"] = [
        {"name": row.name, "description": descriptions[row.name.casefold()]}
        for row in selected
        if row.name.casefold() in descriptions
    ]
    return expanded


def character_visual_prompt(character: Character) -> str:
    """Returns user-authored character details as clean comma-separated prompt tags."""
    values = [character.visual_description, character.description]
    values.extend(_attribute_values(character.attributes))
    tags: list[str] = []
    for value in values:
        if not value.strip():
            continue
        for part in re.split(r"[,;\n.!?]+|\s+(?:y|e|and)\s+", value, flags=re.IGNORECASE):
            normalized = " ".join(part.split()).strip(" -:")
            if normalized and normalized.casefold() not in {tag.casefold() for tag in tags}:
                tags.append(normalized)
    return ", ".join(tags)


def _character_tags(character: Character) -> str:
    return character_visual_prompt(character)


def _attribute_values(attributes: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key, value in attributes.items():
        if isinstance(value, str) and value.strip():
            values.append(f"{key.replace('_', ' ')}: {value.strip()}")
        elif isinstance(value, list):
            texts = [str(item).strip() for item in value if isinstance(item, str) and item.strip()]
            if texts:
                values.append(f"{key.replace('_', ' ')}: {', '.join(texts)}")
    return values


def _constant_replacer(value: str) -> Callable[[re.Match[str]], str]:
    def replace(_match: re.Match[str]) -> str:
        return value

    return replace
