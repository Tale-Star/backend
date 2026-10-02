"""Provision Tale Star model weights into caches outside the source checkout."""

from __future__ import annotations

import argparse

from app.generative_media.infrastructure.model_assets import (
    download_acestep_checkpoints,
    download_configured_loras,
)
from app.shared.config.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-acestep", action="store_true")
    parser.add_argument("--skip-loras", action="store_true")
    arguments = parser.parse_args()
    settings = get_settings()

    if not settings.model_downloads_enabled:
        parser.error("Set MODEL_DOWNLOADS_ENABLED=true to allow downloads.")
    if not arguments.skip_acestep:
        if settings.acestep_project_root is None:
            parser.error("Set ACESTEP_PROJECT_ROOT to the ACE-Step 1.5 source installation.")
        path = download_acestep_checkpoints(settings, settings.acestep_project_root)
        print(f"ACE-Step checkpoints stored at {path}")
    if not arguments.skip_loras:
        for path in download_configured_loras(settings):
            print(f"LoRA stored at {path}")


if __name__ == "__main__":
    main()
