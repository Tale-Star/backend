"""Pruebas de integración del vertical slice GenerativeMedia."""

import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.generative_media.application.generation_ports import GeneratedMedia
from app.generative_media.application.generation_worker import GenerationWorker
from app.generative_media.domain.generation_job import (
    GenerationJob,
    GenerationType,
)
from app.generative_media.infrastructure.fake_generators import (
    FakeImageGeneratorAdapter,
    FakeMusicGeneratorAdapter,
)
from app.generative_media.infrastructure.generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.generative_media.infrastructure.generation_queue_lock import FileGenerationQueueLock
from app.generative_media.infrastructure.local_asset_storage import LocalAssetStorage
from app.shared.config.settings import Settings

IMAGE_REQUEST = {
    "Action": "walking",
    "Emotion": "joyful",
    "Scene": "a garden under the stars",
    "Moment": "the first meeting",
    "Extra": "soft light",
    "FreePrompt": "storybook illustration",
    "Style": "watercolor",
    "Characters": ["Mira"],
    "Objects": ["lantern"],
    "Seed": 41,
}

MUSIC_REQUEST = {
    "Caption": "A gentle night song",
    "Duration": 10,
    "Bpm": 120,
    "Voice": "Female · Powerful",
    "Language": "Español",
    "Output": "song",
    "Genre": ["folk"],
    "Mood": ["hopeful"],
    "Instruments": ["piano"],
    "Production": ["warm"],
    "Sections": [{"Type": "Verse", "Modifier": "soft", "Text": "Buenas noches"}],
    "Seed": 7,
}


def test_image_job_is_created_and_status_can_be_queried(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = api_client.post(
        "/api/v1/generations/images", json=IMAGE_REQUEST, headers=auth_headers
    )

    assert created.status_code == 202
    job = created.json()
    assert job["type"] == "Image"
    assert job["status"] == "Pending"
    assert job["payload"] == {**IMAGE_REQUEST, "CharacterDescriptions": []}
    assert job["seed"] == 41
    assert job["attempts"] == 0

    queried = api_client.get(f"/api/v1/generations/{job['id']}", headers=auth_headers)
    assert queried.status_code == 200
    assert queried.json() == job


def test_image_job_expands_owned_character_mentions(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    created_character = api_client.post(
        "/api/v1/characters",
        json={
            "name": "Lumi",
            "description": "",
            "visual_description": "Una criatura violeta, pequeña y luminosa",
            "attributes": {},
        },
        headers=auth_headers,
    )
    assert created_character.status_code == 201

    response = api_client.post(
        "/api/v1/generations/images",
        json={**IMAGE_REQUEST, "Action": "@Lumi salta sobre @Lumi", "Characters": ["Lumi"]},
        headers=auth_headers,
    )

    assert response.status_code == 202
    payload = response.json()["payload"]
    assert "@Lumi" not in payload["Action"]
    assert payload["CharacterDescriptions"] == [
        {"name": "Lumi", "description": "Una criatura violeta, pequeña, luminosa"}
    ]
    assert "criatura violeta" in payload["Action"].casefold()


def test_image_job_includes_selected_backend_style_profile_details(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    created_profile = api_client.post(
        "/api/v1/style-profiles",
        json={
            "name": "Flat Anime Style",
            "description": "Flat colors for storybook art",
            "prompt_modifier": "clean flat colors, soft outlines",
            "visual_settings": {
                "zimage_lora_asset": "flat_anime_style_zit",
                "zimage_lora_scale": 0.8,
            },
        },
        headers=auth_headers,
    )
    assert created_profile.status_code == 201

    response = api_client.post(
        "/api/v1/generations/images",
        json={**IMAGE_REQUEST, "Style": "Flat Anime Style"},
        headers=auth_headers,
    )

    assert response.status_code == 202
    assert response.json()["payload"]["StyleProfileDetails"] == {
        "prompt_modifier": "clean flat colors, soft outlines",
        "visual_settings": {
            "zimage_lora_asset": "flat_anime_style_zit",
            "zimage_lora_scale": 0.8,
        },
    }


def test_music_job_persists_frontend_contract(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = api_client.post(
        "/api/v1/generations/music", json=MUSIC_REQUEST, headers=auth_headers
    )

    assert response.status_code == 202
    job = response.json()
    assert job["type"] == "Music"
    assert job["status"] == "Pending"
    assert job["payload"] == MUSIC_REQUEST
    assert job["payload"]["Sections"][0] == {
        "Type": "Verse",
        "Modifier": "soft",
        "Text": "Buenas noches",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Duration", 9),
        ("Duration", 601),
        ("Bpm", 29),
        ("Bpm", 301),
        ("Language", "French"),
        ("Output", "album"),
    ],
)
def test_music_request_validates_frontend_limits(
    api_client: TestClient, auth_headers: dict[str, str], field: str, value: object
) -> None:
    request = {**MUSIC_REQUEST, field: value}

    response = api_client.post("/api/v1/generations/music", json=request, headers=auth_headers)

    assert response.status_code == 422


def test_image_request_validates_seed(api_client: TestClient, auth_headers: dict[str, str]) -> None:
    response = api_client.post(
        "/api/v1/generations/images",
        json={**IMAGE_REQUEST, "Seed": 4_294_967_296},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_pending_job_is_processed_and_asset_is_written(
    api_app: FastAPI,
    api_client: TestClient,
    auth_headers: dict[str, str],
    test_settings: Settings,
) -> None:
    created = api_client.post(
        "/api/v1/generations/images", json=IMAGE_REQUEST, headers=auth_headers
    )
    job_id = UUID(created.json()["id"])
    storage = LocalAssetStorage(test_settings.media_directory)

    with api_app.state.session_factory() as session:
        worker = GenerationWorker(
            SqlAlchemyGenerationJobRepository(session),
            _InspectingImageGenerator(api_client, job_id, auth_headers),
            FakeMusicGeneratorAdapter(),
            storage,
        )
        assert worker.run_once() == job_id

    completed = api_client.get(f"/api/v1/generations/{job_id}", headers=auth_headers)
    assert completed.status_code == 200
    job = completed.json()
    assert job["status"] == "Succeeded"
    assert job["attempts"] == 1
    assert job["started_at"] is not None
    assert job["completed_at"] is not None
    asset_path = Path(test_settings.media_directory) / job["result"]["asset_path"]
    assert asset_path.is_file()
    assert asset_path.read_text(encoding="utf-8").startswith("<svg")
    assert job["result"]["asset_id"]
    assert job["result"]["path"] == job["result"]["asset_path"]
    assert job["result"]["seed"] == 41
    assert job["result"]["width"] == 512
    assert job["result"]["height"] == 512

    media_response = api_client.get(f"/api/v1/media/{job['result']['path']}", headers=auth_headers)
    assert media_response.status_code == 200
    assert media_response.headers["content-type"].startswith("image/svg+xml")
    assert media_response.content.startswith(b"<svg")
    media_by_id = api_client.get(
        f"/api/v1/media/assets/{job['result']['asset_id']}", headers=auth_headers
    )
    assert media_by_id.status_code == 200
    assert media_by_id.headers["content-type"].startswith("image/svg+xml")


def test_music_worker_writes_a_valid_wav_file(
    api_app: FastAPI,
    api_client: TestClient,
    auth_headers: dict[str, str],
    test_settings: Settings,
) -> None:
    created = api_client.post("/api/v1/generations/music", json=MUSIC_REQUEST, headers=auth_headers)
    job_id = UUID(created.json()["id"])

    with api_app.state.session_factory() as session:
        worker = _worker(session, LocalAssetStorage(test_settings.media_directory))
        assert worker.run_once() == job_id

    completed = api_client.get(f"/api/v1/generations/{job_id}", headers=auth_headers).json()
    assert completed["status"] == "Succeeded"
    asset_path = Path(test_settings.media_directory) / completed["result"]["asset_path"]
    with wave.open(str(asset_path), "rb") as generated_audio:
        assert generated_audio.getnchannels() == 1
        assert generated_audio.getframerate() == FakeMusicGeneratorAdapter.sample_rate
        assert (
            generated_audio.getnframes()
            == MUSIC_REQUEST["Duration"] * FakeMusicGeneratorAdapter.sample_rate
        )
    assert completed["result"]["duration"] == 10.0
    assert completed["result"]["bpm"] == 120
    assert completed["result"]["language"] == "Español"


def test_media_endpoint_rejects_traversal(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = api_client.get("/api/v1/media/%2e%2e%2foutside.txt", headers=auth_headers)

    assert response.status_code == 404


def test_flac_media_uses_the_persisted_mime_type(
    api_app: FastAPI,
    api_client: TestClient,
    auth_headers: dict[str, str],
    test_settings: Settings,
) -> None:
    user_id = UUID(api_client.get("/api/v1/auth/me", headers=auth_headers).json()["id"])
    asset_id = uuid4()
    storage = LocalAssetStorage(test_settings.media_directory)
    asset_path = storage.save(asset_id, ".flac", b"fLaC test bytes", user_id)
    job = GenerationJob(type=GenerationType.MUSIC, payload={}, owner_id=user_id)
    job.mark_processing()
    job.mark_succeeded({"asset_id": str(asset_id), "path": asset_path, "media_type": "audio/flac"})
    with api_app.state.session_factory() as session:
        SqlAlchemyGenerationJobRepository(session).add(job)

    by_id = api_client.get(f"/api/v1/media/assets/{asset_id}", headers=auth_headers)
    by_path = api_client.get(f"/api/v1/media/{asset_path}", headers=auth_headers)

    assert by_id.status_code == by_path.status_code == 200
    assert by_id.headers["content-type"] == "audio/flac"
    assert by_path.headers["content-type"] == "audio/flac"


def test_media_endpoint_enforces_owner_and_missing_asset_returns_404(
    api_app: FastAPI,
    api_client: TestClient,
    auth_headers: dict[str, str],
    test_settings: Settings,
) -> None:
    created = api_client.post(
        "/api/v1/generations/images", json=IMAGE_REQUEST, headers=auth_headers
    )
    job_id = UUID(created.json()["id"])
    with api_app.state.session_factory() as session:
        worker = GenerationWorker(
            SqlAlchemyGenerationJobRepository(session),
            FakeImageGeneratorAdapter(),
            FakeMusicGeneratorAdapter(),
            LocalAssetStorage(test_settings.media_directory),
        )
        assert worker.run_once() == job_id

    result = api_client.get(f"/api/v1/generations/{job_id}", headers=auth_headers).json()["result"]
    other_account = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "display_name": "Other Account",
            "password": "other-password-123",
        },
    )
    assert other_account.status_code == 201
    other_headers = {"Authorization": f"Bearer {other_account.json()['access_token']}"}

    denied = api_client.get(f"/api/v1/media/{result['path']}", headers=other_headers)
    denied_by_id = api_client.get(
        f"/api/v1/media/assets/{result['asset_id']}", headers=other_headers
    )
    owner_directory = result["path"].split("/")[0]
    missing = api_client.get(
        f"/api/v1/media/{owner_directory}/00/{uuid4().hex}.png",
        headers=auth_headers,
    )

    assert denied.status_code == 404
    assert denied_by_id.status_code == 404
    assert missing.status_code == 404
    assert (
        api_client.get(f"/api/v1/media/assets/{uuid4()}", headers=auth_headers).status_code == 404
    )


def test_domain_enforces_pending_processing_succeeded_transitions() -> None:
    job = GenerationJob(type=GenerationType.IMAGE, payload=IMAGE_REQUEST)
    assert job.status.value == "Pending"

    job.mark_processing()
    assert job.status.value == "Processing"
    assert job.attempts == 1

    job.mark_succeeded({"asset_path": "aa/example.svg"})
    assert job.status.value == "Succeeded"
    assert job.started_at is not None
    assert job.completed_at is not None


def test_worker_persists_controlled_generation_failure(
    api_app: FastAPI,
    api_client: TestClient,
    auth_headers: dict[str, str],
    test_settings: Settings,
) -> None:
    created = api_client.post(
        "/api/v1/generations/images", json=IMAGE_REQUEST, headers=auth_headers
    )
    job_id = UUID(created.json()["id"])

    with api_app.state.session_factory() as session:
        worker = GenerationWorker(
            SqlAlchemyGenerationJobRepository(session),
            _FailingImageGenerator(),
            FakeMusicGeneratorAdapter(),
            LocalAssetStorage(test_settings.media_directory),
        )
        assert worker.run_once() == job_id

    failed = api_client.get(f"/api/v1/generations/{job_id}", headers=auth_headers)
    assert failed.status_code == 200
    assert failed.json()["status"] == "Failed"
    assert failed.json()["error_message"] == "controlled generator failure"
    assert failed.json()["completed_at"] is not None


def test_worker_marks_interrupted_job_failed_before_shutdown(
    api_app: FastAPI, api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = api_client.post(
        "/api/v1/generations/images", json=IMAGE_REQUEST, headers=auth_headers
    )
    job_id = UUID(created.json()["id"])

    with api_app.state.session_factory() as session:
        queue_lock = FileGenerationQueueLock(api_app.state.settings.gpu_queue_lock_path)
        worker = GenerationWorker(
            SqlAlchemyGenerationJobRepository(session),
            _InterruptingImageGenerator(),
            FakeMusicGeneratorAdapter(),
            LocalAssetStorage(api_app.state.settings.media_directory),
            queue_lock=queue_lock,
        )
        with pytest.raises(KeyboardInterrupt):
            worker.run_once()
        assert queue_lock.try_acquire()
        queue_lock.release()

    interrupted = api_client.get(f"/api/v1/generations/{job_id}", headers=auth_headers)
    assert interrupted.json()["status"] == "Failed"
    assert interrupted.json()["error_message"] == "Generation interrupted by worker shutdown."


def test_unknown_generation_job_returns_404(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = api_client.get(f"/api/v1/generations/{UUID(int=0)}", headers=auth_headers)

    assert response.status_code == 404


def test_two_workers_cannot_claim_the_same_job(
    api_app: FastAPI,
) -> None:
    with api_app.state.session_factory() as session:
        SqlAlchemyGenerationJobRepository(session).add(
            GenerationJob(type=GenerationType.IMAGE, payload=IMAGE_REQUEST)
        )

    def claim() -> GenerationJob | None:
        with api_app.state.session_factory() as session:
            return SqlAlchemyGenerationJobRepository(session).claim_next()

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(lambda _index: claim(), range(2)))

    assert sum(job is not None for job in claims) == 1


def _worker(session: Session, storage: LocalAssetStorage) -> GenerationWorker:
    return GenerationWorker(
        SqlAlchemyGenerationJobRepository(session),
        FakeImageGeneratorAdapter(),
        FakeMusicGeneratorAdapter(),
        storage,
    )


class _InspectingImageGenerator:
    def __init__(self, client: TestClient, job_id: UUID, auth_headers: dict[str, str]) -> None:
        self._client = client
        self._job_id = job_id
        self._auth_headers = auth_headers

    def generate(self, payload: dict[str, Any], seed: int | None) -> GeneratedMedia:
        status = self._client.get(
            f"/api/v1/generations/{self._job_id}", headers=self._auth_headers
        ).json()["status"]
        if status != "Processing":
            raise AssertionError(f"Expected persisted Processing status, received {status}")
        return FakeImageGeneratorAdapter().generate(payload, seed)


class _FailingImageGenerator:
    def generate(self, _payload: dict[str, Any], _seed: int | None) -> GeneratedMedia:
        raise RuntimeError("controlled generator failure")


class _InterruptingImageGenerator:
    def generate(self, _payload: dict[str, Any], _seed: int | None) -> GeneratedMedia:
        raise KeyboardInterrupt
