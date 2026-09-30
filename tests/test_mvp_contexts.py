"""API tests for identity, creative authoring and library ownership rules."""

from uuid import UUID

from fastapi.testclient import TestClient

from app.generative_media.application.generation_worker import GenerationWorker
from app.generative_media.infrastructure.fake_generators import (
    FakeImageGeneratorAdapter,
    FakeMusicGeneratorAdapter,
)
from app.generative_media.infrastructure.generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.generative_media.infrastructure.local_asset_storage import LocalAssetStorage
from app.shared.config.settings import Settings


def test_registration_login_profile_and_duplicate_email(
    api_client: TestClient,
) -> None:
    body = {
        "email": "Parent@Example.com",
        "display_name": "Parent",
        "password": "a-strong-password-123",
    }
    registered = api_client.post("/api/v1/auth/register", json=body)
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert api_client.get("/api/v1/auth/me", headers=headers).json()["email"] == (
        "parent@example.com"
    )

    logged_in = api_client.post(
        "/api/v1/auth/login",
        json={"email": "parent@example.com", "password": body["password"]},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["id"] == registered.json()["user"]["id"]
    assert api_client.post("/api/v1/auth/register", json=body).status_code == 409
    assert (
        api_client.post(
            "/api/v1/auth/login",
            json={"email": body["email"], "password": "incorrect-password"},
        ).status_code
        == 401
    )
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_parental_pin_is_hashed_and_validated(
    api_client: TestClient,
) -> None:
    registered = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "pin@example.com",
            "display_name": "Pin Parent",
            "password": "a-strong-password-123",
            "parental_pin": "2468",
        },
    )
    assert registered.status_code == 201
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    assert registered.json()["user"]["pin_configured"] is True
    assert api_client.post(
        "/api/v1/auth/parental-pin/validate", json={"pin": "2468"}, headers=headers
    ).json() == {"valid": True}
    assert api_client.post(
        "/api/v1/auth/parental-pin/validate", json={"pin": "0000"}, headers=headers
    ).json() == {"valid": False}
    assert (
        api_client.put(
            "/api/v1/auth/parental-pin",
            json={"current_password": "a-strong-password-123", "pin": "1357"},
            headers=headers,
        ).status_code
        == 200
    )
    assert api_client.post(
        "/api/v1/auth/parental-pin/validate", json={"pin": "1357"}, headers=headers
    ).json() == {"valid": True}

    user_id = UUID(registered.json()["user"]["id"])
    with api_client.app.state.session_factory() as session:
        from app.identity_access.infrastructure.user_model import UserRecord

        stored = session.get(UserRecord, user_id)
        assert stored is not None
        assert stored.parental_pin_hash != "1357"
        assert stored.parental_pin_hash is not None
        assert stored.parental_pin_hash.startswith("$argon2")


def test_characters_and_scenarios_are_owned_and_editable(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    character = api_client.post(
        "/api/v1/characters",
        json={"name": "Mira", "visual_description": "blue cloak", "attributes": {"age": 8}},
        headers=auth_headers,
    )
    assert character.status_code == 201
    character_id = character.json()["id"]
    changed = api_client.patch(
        f"/api/v1/characters/{character_id}",
        json={"description": "A curious explorer"},
        headers=auth_headers,
    )
    assert changed.status_code == 200
    assert changed.json()["description"] == "A curious explorer"
    assert api_client.get("/api/v1/characters?q=mira", headers=auth_headers).json()[0]["id"] == (
        character_id
    )

    scenario = api_client.post(
        "/api/v1/scenarios",
        json={"name": "Moon garden", "seed": 27},
        headers=auth_headers,
    )
    assert scenario.status_code == 201
    scenario_id = scenario.json()["id"]
    assert (
        api_client.patch(
            f"/api/v1/scenarios/{scenario_id}",
            json={"seed": None},
            headers=auth_headers,
        ).json()["seed"]
        is None
    )

    other = _register(api_client, "other@example.com")
    assert api_client.get(f"/api/v1/characters/{character_id}", headers=other).status_code == 404
    assert (
        api_client.patch(
            f"/api/v1/scenarios/{scenario_id}", json={"name": "stolen"}, headers=other
        ).status_code
        == 404
    )
    assert api_client.delete(f"/api/v1/characters/{character_id}", headers=other).status_code == 404
    assert (
        api_client.get(f"/api/v1/characters/{UUID(int=0)}", headers=auth_headers).status_code == 404
    )


def test_stories_pages_and_page_character_references(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    character = api_client.post(
        "/api/v1/characters", json={"name": "Pip"}, headers=auth_headers
    ).json()
    scenario = api_client.post(
        "/api/v1/scenarios", json={"name": "Forest", "seed": 81}, headers=auth_headers
    ).json()
    style = api_client.post(
        "/api/v1/style-profiles",
        json={"name": "Watercolor", "prompt_modifier": "soft paint"},
        headers=auth_headers,
    ).json()
    story = api_client.post(
        "/api/v1/stories",
        json={
            "title": "The lantern",
            "description": "Written by the user",
            "scenario_id": scenario["id"],
            "style_profile_id": style["id"],
            "seed": 99,
        },
        headers=auth_headers,
    )
    assert story.status_code == 201
    story_id = story.json()["id"]
    page = api_client.post(
        f"/api/v1/stories/{story_id}/pages",
        json={
            "page_number": 1,
            "action": "Mira opens the door",
            "text": "A user authored sentence.",
            "visual_config": {"camera": "wide"},
            "character_ids": [character["id"]],
            "seed": 101,
        },
        headers=auth_headers,
    )
    assert page.status_code == 201
    page_id = page.json()["id"]
    assert page.json()["character_ids"] == [character["id"]]
    assert (
        api_client.patch(
            f"/api/v1/stories/{story_id}/pages/{page_id}",
            json={"text": "Edited page by page."},
            headers=auth_headers,
        ).json()["text"]
        == "Edited page by page."
    )
    assert (
        api_client.patch(
            f"/api/v1/stories/{story_id}/pages/{page_id}",
            json={"seed": None},
            headers=auth_headers,
        ).json()["seed"]
        is None
    )
    assert (
        api_client.get(f"/api/v1/stories/{story_id}/pages", headers=auth_headers).json()[0]["seed"]
        is None
    )
    duplicate = api_client.post(
        f"/api/v1/stories/{story_id}/pages",
        json={"page_number": 1},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409
    assert (
        api_client.get(f"/api/v1/stories/{UUID(int=0)}/pages", headers=auth_headers).status_code
        == 404
    )

    other = _register(api_client, "story-owner@example.com")
    assert api_client.get(f"/api/v1/stories/{story_id}", headers=other).status_code == 404
    assert (
        api_client.patch(
            f"/api/v1/stories/{story_id}/pages/{page_id}",
            json={"text": "unauthorized"},
            headers=other,
        ).status_code
        == 404
    )


def test_library_references_search_favorites_and_ownership(
    api_client: TestClient,
    api_app,
    auth_headers: dict[str, str],
    test_settings: Settings,
) -> None:
    story = api_client.post(
        "/api/v1/stories", json={"title": "A story for the library"}, headers=auth_headers
    ).json()
    image = api_client.post(
        "/api/v1/generations/images",
        json={"Action": "look", "Seed": 55},
        headers=auth_headers,
    ).json()
    music = api_client.post(
        "/api/v1/generations/music",
        json={"Duration": 10, "Bpm": 90, "Language": "English", "Output": "instrumental"},
        headers=auth_headers,
    ).json()
    with api_app.state.session_factory() as session:
        worker = GenerationWorker(
            SqlAlchemyGenerationJobRepository(session),
            FakeImageGeneratorAdapter(),
            FakeMusicGeneratorAdapter(),
            LocalAssetStorage(test_settings.media_directory),
        )
        assert worker.run_once() == UUID(image["id"])
        assert worker.run_once() == UUID(music["id"])

    image_result = api_client.get(
        f"/api/v1/generations/{image['id']}", headers=auth_headers
    ).json()["result"]
    music_result = api_client.get(
        f"/api/v1/generations/{music['id']}", headers=auth_headers
    ).json()["result"]
    references = [
        ("story", story["id"]),
        ("image", image_result["asset_id"]),
        ("music", music_result["asset_id"]),
    ]
    created = []
    for item_type, resource_id in references:
        response = api_client.post(
            "/api/v1/library",
            json={"type": item_type, "resource_id": resource_id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        created.append(response.json())
    assert created[0]["name"] == "A story for the library"
    assert created[1]["resource_url"] == f"/api/v1/media/assets/{image_result['asset_id']}"
    assert created[2]["resource_url"] == f"/api/v1/media/assets/{music_result['asset_id']}"

    favorite_id = created[1]["id"]
    patched = api_client.patch(
        f"/api/v1/library/{favorite_id}",
        json={"favorite": True, "name": "Moon image"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["favorite"] is True
    assert (
        api_client.get(
            "/api/v1/library?type=image&favorite=true&q=moon", headers=auth_headers
        ).json()[0]["id"]
        == favorite_id
    )
    assert len(api_client.get("/api/v1/library", headers=auth_headers).json()) == 3
    duplicate = api_client.post(
        "/api/v1/library",
        json={"type": "image", "resource_id": image_result["asset_id"]},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409
    assert api_client.get(f"/api/v1/library/{favorite_id}", headers=auth_headers).status_code == 200
    other = _register(api_client, "library-owner@example.com")
    assert api_client.get(f"/api/v1/library/{favorite_id}", headers=other).status_code == 404
    assert api_client.delete(f"/api/v1/library/{favorite_id}", headers=other).status_code == 404
    assert (
        api_client.post(
            "/api/v1/library",
            json={"type": "story", "resource_id": story["id"]},
            headers=other,
        ).status_code
        == 404
    )
    assert (
        api_client.delete(f"/api/v1/library/{favorite_id}", headers=auth_headers).status_code == 204
    )
    assert api_client.get(f"/api/v1/library/{favorite_id}", headers=auth_headers).status_code == 404


def test_generation_jobs_and_media_are_private(
    api_client: TestClient, api_app, auth_headers: dict[str, str], test_settings: Settings
) -> None:
    created = api_client.post(
        "/api/v1/generations/images", json={"Seed": 4}, headers=auth_headers
    ).json()
    with api_app.state.session_factory() as session:
        GenerationWorker(
            SqlAlchemyGenerationJobRepository(session),
            FakeImageGeneratorAdapter(),
            FakeMusicGeneratorAdapter(),
            LocalAssetStorage(test_settings.media_directory),
        ).run_once()
    result = api_client.get(f"/api/v1/generations/{created['id']}", headers=auth_headers).json()[
        "result"
    ]
    other = _register(api_client, "media-owner@example.com")
    assert api_client.get(f"/api/v1/generations/{created['id']}", headers=other).status_code == 404
    assert api_client.get(f"/api/v1/media/{result['path']}", headers=other).status_code == 404
    assert (
        api_client.get(f"/api/v1/media/{result['path']}", headers=auth_headers).status_code == 200
    )


def test_validation_errors_do_not_echo_passwords(api_client: TestClient) -> None:
    secret_input = "do-not-echo-this-password"
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "not-email", "display_name": "x", "password": secret_input},
    )
    assert response.status_code == 422
    assert secret_input not in response.text


def test_unknown_endpoint_uses_the_standard_error_envelope(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/no-such-endpoint")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "http_404", "message": "Not Found"}}


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Another adult",
            "password": "another-strong-password-123",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
