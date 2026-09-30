"""Pruebas del adaptador de archivos local."""

from uuid import uuid4

import pytest

from app.generative_media.infrastructure.local_asset_storage import LocalAssetStorage


def test_local_storage_round_trips_asset_bytes(tmp_path) -> None:
    storage = LocalAssetStorage(tmp_path / "assets")
    asset_id = uuid4()
    content = b"image bytes"

    key = storage.save(asset_id, ".PNG", content)
    with storage.open(asset_id, ".png") as saved_asset:
        assert saved_asset.read() == content

    assert key == f"{asset_id.hex[:2]}/{asset_id.hex}.png"
    storage.delete(asset_id, ".png")
    assert not (storage.root / key).exists()


def test_local_storage_rejects_path_extensions(tmp_path) -> None:
    storage = LocalAssetStorage(tmp_path / "assets")

    with pytest.raises(ValueError):
        storage.save(uuid4(), "../secret", b"content")
