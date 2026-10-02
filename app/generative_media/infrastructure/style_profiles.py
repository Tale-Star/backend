"""Resolución privada de StyleProfile a instrucciones y configuración visual."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class StyleProfileConfiguration:
    """Configuración interna asociada a un perfil que envía el frontend."""

    prompt_instruction: str
    lora_path: Path | None = None
    lora_scale: float = 1.0
    lora_asset_id: str | None = None


class StyleProfileRegistry:
    """Mapea nombres de perfil a instrucciones y adapters visuales opcionales."""

    def __init__(self, configuration_file: Path | None = None) -> None:
        self._configuration_file = configuration_file
        self._profiles = self._read_profiles(configuration_file)

    def resolve(self, profile_name: str) -> StyleProfileConfiguration:
        normalized_name = profile_name.strip()
        if not normalized_name:
            return StyleProfileConfiguration(prompt_instruction="")
        profile = self._profiles.get(normalized_name.casefold())
        if profile is not None:
            return profile
        return StyleProfileConfiguration(prompt_instruction=f"Visual style: {normalized_name}")

    def _read_profiles(
        self, configuration_file: Path | None
    ) -> dict[str, StyleProfileConfiguration]:
        if configuration_file is None:
            return {}
        if not configuration_file.is_file():
            raise FileNotFoundError(f"No existe el archivo de StyleProfiles: {configuration_file}")

        raw: Any = json.loads(configuration_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("ZIMAGE_STYLE_PROFILES_FILE debe contener un objeto JSON.")

        profiles: dict[str, StyleProfileConfiguration] = {}
        for name, value in raw.items():
            if not isinstance(name, str) or not isinstance(value, dict):
                raise ValueError("Cada StyleProfile debe apuntar a un objeto de configuración.")
            prompt = value.get("prompt", "")
            lora_path = value.get("lora_path")
            lora_asset_id = value.get("lora_asset")
            lora_scale = value.get("lora_scale", 1.0)
            if not isinstance(prompt, str) or not isinstance(lora_scale, int | float):
                raise ValueError(f"Configuración inválida para StyleProfile {name!r}.")
            if lora_asset_id is not None and not isinstance(lora_asset_id, str):
                raise ValueError(f"lora_asset invalid for StyleProfile {name!r}.")
            if not math.isfinite(lora_scale):
                raise ValueError(f"lora_scale inválido para StyleProfile {name!r}.")
            resolved_lora_path: Path | None = None
            if lora_path is not None:
                if not isinstance(lora_path, str):
                    raise ValueError(f"lora_path inválido para StyleProfile {name!r}.")
                path = Path(lora_path).expanduser()
                if not path.is_absolute():
                    path = configuration_file.parent / path
                resolved_lora_path = path.resolve()
            profiles[name.casefold()] = StyleProfileConfiguration(
                prompt_instruction=prompt,
                lora_path=resolved_lora_path,
                lora_scale=float(lora_scale),
                lora_asset_id=lora_asset_id,
            )
        return profiles
