"""Downloads a small, explicit set of model assets without putting weights in Git."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from app.shared.config.settings import Settings

logger = logging.getLogger(__name__)

ACE_STEP_REPOSITORY = "ACE-Step/Ace-Step1.5"
ACE_STEP_CHECKPOINTS = (
    "acestep-v15-turbo/**",
    "acestep-5Hz-lm-1.7B/**",
    "Qwen3-Embedding-0.6B/**",
    "vae/**",
)


@dataclass(frozen=True, slots=True)
class LoraAsset:
    asset_id: str
    filename: str
    sha256: str
    base_model: str
    download_url: str | None
    source_url: str


LORA_ASSETS: dict[str, LoraAsset] = {
    "flat_anime_style_zit": LoraAsset(
        asset_id="flat_anime_style_zit",
        filename="FlatAnimeStyle_ZIT.safetensors",
        sha256="b2ba44ea67c12376d82d951806f346594aeaecc4e9759092c49cdc46204300d4",
        base_model="z-image-turbo",
        download_url="https://civitai.com/api/download/models/2513340",
        source_url="https://civitai.com/models/421532",
    ),
    "amelicart_illustration": LoraAsset(
        asset_id="amelicart_illustration",
        filename="z_lora_amelicart_000001750.safetensors",
        sha256="b0a635841ac4c2e7a66ce8a67e4f3f5aedb4cf5e715147f1a7fee348b64a9cd9",
        base_model="z-image-turbo",
        download_url="https://civitai.com/api/download/models/2579850",
        source_url="https://civitai.com/models/886605?modelVersionId=2579850",
    ),
    "flat_color_zimage_base": LoraAsset(
        asset_id="flat_color_zimage_base",
        filename="zimagebase_flat_color_v2.1.safetensors",
        sha256="8cbc55449e4b22121abd54c35dee02f059e4c4e9bfa0c86b8ded8c35b0ededdd6",
        # The published source lists Z-Image Base, and the project's owner verified
        # this exact file with the configured Turbo pipeline on the target machine.
        base_model="z-image-turbo",
        download_url="https://civitai.com/api/download/models/2637093",
        source_url="https://civitai.com/models/1132089?modelVersionId=2637093",
    ),
}


def resolve_lora_asset(settings: Settings, asset_id: str) -> Path:
    """Returns a verified LoRA path, downloading only when explicitly enabled."""
    asset = LORA_ASSETS.get(asset_id)
    if asset is None:
        raise ValueError(f"Unknown Z-Image LoRA asset: {asset_id}")
    if asset.base_model != settings.zimage_model_variant:
        raise RuntimeError(
            f"{asset.filename} targets {asset.base_model}, but the configured pipeline is "
            f"{settings.zimage_model_variant}. Choose a LoRA trained for the active model."
        )

    destination = settings.zimage_lora_directory.expanduser() / asset.filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        _verify_asset(destination, asset)
        return destination.resolve()

    for source in _local_lora_candidates(settings, asset):
        if source.is_file():
            _verify_asset(source, asset)
            shutil.copyfile(source, destination)
            return destination.resolve()

    if not settings.model_downloads_enabled:
        raise FileNotFoundError(
            f"Missing LoRA {asset.filename}. Enable MODEL_DOWNLOADS_ENABLED or place it at "
            f"{destination}. Source: {asset.source_url}"
        )
    if asset.download_url is None:
        raise RuntimeError(
            f"Automatic download is not configured for {asset.filename}; place the verified "
            f"file at {destination}. Source: {asset.source_url}"
        )

    _download_verified(asset, destination)
    return destination.resolve()


def download_acestep_checkpoints(settings: Settings, project_root: Path) -> Path:
    """Fetch only the ACE-Step 1.5 model folders used by this application (~6 GiB)."""
    checkpoint_directory = project_root.expanduser().resolve() / "checkpoints"
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(settings.model_cache_directory.expanduser().resolve()))
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=ACE_STEP_REPOSITORY,
        allow_patterns=list(ACE_STEP_CHECKPOINTS),
        cache_dir=str(settings.model_cache_directory.expanduser().resolve()),
        local_dir=str(checkpoint_directory),
        token=os.getenv("HF_TOKEN") or None,
    )
    return checkpoint_directory


def download_configured_loras(settings: Settings) -> list[Path]:
    """Downloads the registered, owner-verified LoRAs for the configured pipeline."""
    return [resolve_lora_asset(settings, asset.asset_id) for asset in LORA_ASSETS.values()]


def _local_lora_candidates(settings: Settings, asset: LoraAsset) -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[3].parent
    return (
        settings.model_cache_directory.expanduser() / "loras" / asset.filename,
        root / asset.filename,
    )


def _verify_asset(path: Path, asset: LoraAsset) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest().casefold() != asset.sha256:
        raise ValueError(f"SHA-256 mismatch for {asset.filename}; the file was not accepted.")


def _download_verified(asset: LoraAsset, destination: Path) -> None:
    request = Request(asset.download_url or "", headers={"User-Agent": "TaleStar/1.0 model setup"})
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.", suffix=".partial", dir=destination.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        digest = hashlib.sha256()
        try:
            with urlopen(request, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
                    digest.update(chunk)
            if digest.hexdigest().casefold() != asset.sha256:
                raise ValueError(f"SHA-256 mismatch while downloading {asset.filename}.")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path.replace(destination)
            logger.info("Downloaded verified LoRA asset %s", asset.asset_id)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
