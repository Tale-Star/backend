"""CPU-only Spanish-to-English prompt translation for image generation."""

from __future__ import annotations

import re
from importlib import import_module
from typing import Any

import langid  # type: ignore[import-untyped]

from app.shared.config.settings import Settings

SPANISH_MARKERS = frozenset(
    {
        "al",
        "como",
        "con",
        "del",
        "desde",
        "donde",
        "el",
        "ella",
        "ellos",
        "en",
        "es",
        "esta",
        "este",
        "hay",
        "hola",
        "la",
        "las",
        "lo",
        "los",
        "para",
        "pero",
        "por",
        "que",
        "se",
        "sin",
        "son",
        "su",
        "una",
        "uno",
        "unos",
        "unas",
        "y",
    }
)


class PromptTranslator:
    """Lazily loads the MarianMT translator only when a Spanish prompt is received."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None

    def translate_if_spanish(self, text: str) -> str:
        if not text.strip() or not _is_spanish(text):
            return text
        self._load()
        if self._model is None or self._tokenizer is None:
            return text

        translations: list[str] = []
        for chunk in _chunks(text):
            encoded = self._tokenizer(
                chunk,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            generated = self._model.generate(**encoded, max_new_tokens=512, num_beams=1)
            translations.append(self._tokenizer.decode(generated[0], skip_special_tokens=True))
        return " ".join(part.strip() for part in translations if part.strip())

    def _load(self) -> None:
        if self._model is not None:
            return
        torch = import_module("torch")
        transformers = import_module("transformers")
        cache_directory = self._settings.model_cache_directory.expanduser().resolve()
        cache_directory.mkdir(parents=True, exist_ok=True)
        local_files_only = not self._settings.model_downloads_enabled
        self._tokenizer = transformers.AutoTokenizer.from_pretrained(
            self._settings.prompt_translation_model,
            cache_dir=str(cache_directory),
            local_files_only=local_files_only,
        )
        self._model = transformers.AutoModelForSeq2SeqLM.from_pretrained(
            self._settings.prompt_translation_model,
            cache_dir=str(cache_directory),
            local_files_only=local_files_only,
        ).to("cpu")
        self._model.eval()
        self._torch = torch


def translate_prompt(translator: PromptTranslator, text: str) -> str:
    """Runs model inference without autograd while keeping the translator injectable."""
    if not text.strip() or not _is_spanish(text):
        return translator.translate_if_spanish(text)
    translator._load()
    torch = translator._torch
    if torch is None:
        return translator.translate_if_spanish(text)
    with torch.inference_mode():
        return translator.translate_if_spanish(text)


def _chunks(text: str, limit: int = 850) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        while len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:limit])
            sentence = sentence[limit:]
        candidate = f"{current} {sentence}".strip()
        if len(candidate) > limit and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _is_spanish(text: str) -> bool:
    if any(character in text.casefold() for character in "áéíóúüñ¿¡"):
        return True
    words = set(re.findall(r"\b[\w]+\b", text.casefold()))
    if words.intersection(SPANISH_MARKERS):
        return True
    return langid.classify(text)[0] == "es"
