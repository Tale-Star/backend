"""Generadores deterministas de desarrollo sin dependencias de IA."""

import io
import math
import secrets
import wave
from html import escape
from typing import Any

from app.generative_media.application.generation_ports import GeneratedMedia


class FakeImageGeneratorAdapter:
    """Crea una imagen SVG simple con detalles de la solicitud."""

    def load(self) -> None:
        """El adapter fake no mantiene un modelo en memoria."""

    def unload(self) -> None:
        """El adapter fake no mantiene un modelo en memoria."""

    def generate(self, payload: dict[str, Any], seed: int | None) -> GeneratedMedia:
        effective_seed = seed if seed is not None else secrets.randbelow(4_294_967_296)
        description = " — ".join(
            str(payload.get(key, ""))
            for key in ("Action", "Scene", "FreePrompt", "Style")
            if payload.get(key)
        )
        if not description:
            description = "Tale Star fake image"
        seed_line = f"Seed: {effective_seed} (fake adapter)"
        svg = f"""<svg
 xmlns="http://www.w3.org/2000/svg"
 width="512"
 height="512"
 viewBox="0 0 512 512">
<defs>
 <linearGradient id="background" x2="1" y2="1">
  <stop stop-color="#402060"/>
  <stop offset="1" stop-color="#ef8c70"/>
 </linearGradient>
</defs>
<rect width="512" height="512" rx="32" fill="url(#background)"/>
<circle cx="256" cy="205" r="92" fill="#ffe4a3" opacity=".92"/>
<text x="256" y="365" fill="white" font-family="sans-serif"
 font-size="20" text-anchor="middle">{escape(description[:120])}</text>
<text x="256" y="405" fill="white" font-family="sans-serif"
 font-size="15" text-anchor="middle">{escape(seed_line)}</text>
</svg>"""
        return GeneratedMedia(
            content=svg.encode("utf-8"),
            extension=".svg",
            media_type="image/svg+xml",
            seed=effective_seed,
            width=512,
            height=512,
        )


class FakeMusicGeneratorAdapter:
    """Crea un WAV mono válido de tono sencillo para probar el flujo."""

    sample_rate = 8000

    def load(self) -> None:
        """El adapter fake no mantiene un modelo en memoria."""

    def unload(self) -> None:
        """El adapter fake no mantiene un modelo en memoria."""

    def generate(self, payload: dict[str, Any], seed: int | None) -> GeneratedMedia:
        duration = payload.get("Duration", 10)
        if not isinstance(duration, int) or not 10 <= duration <= 600:
            raise ValueError("Duration must be between 10 and 600 seconds")

        effective_seed = seed if seed is not None else secrets.randbelow(4_294_967_296)
        frequency = 330 + effective_seed % 220
        frame_count = duration * self.sample_rate
        samples = bytes(
            int(128 + 48 * math.sin(2 * math.pi * frequency * index / self.sample_rate))
            for index in range(frame_count)
        )
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(1)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples)

        return GeneratedMedia(
            content=output.getvalue(),
            extension=".wav",
            media_type="audio/wav",
            seed=effective_seed,
            duration=float(duration),
            bpm=payload.get("Bpm") if isinstance(payload.get("Bpm"), int) else None,
            language=payload.get("Language") if isinstance(payload.get("Language"), str) else None,
        )
