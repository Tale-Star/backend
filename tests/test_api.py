"""Pruebas de los endpoints compartidos de la API."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.shared.config.settings import Settings
from app.shared.errors import AppError


def test_health_routes(test_settings: Settings) -> None:
    application = create_app(test_settings)

    with TestClient(application) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_local_smoke_test_page_is_served_from_the_api(test_settings: Settings) -> None:
    application = create_app(test_settings)

    with TestClient(application) as client:
        response = client.get("/smoke-test")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Generate Test Music" in response.text
    assert "Generate Test Image" in response.text


def test_openapi_lists_frontend_routes_and_consistent_responses(test_settings: Settings) -> None:
    application = create_app(test_settings)

    with TestClient(application) as client:
        schema = client.get("/openapi.json").json()

    assert "creative-authoring" in {tag["name"] for tag in schema["tags"]}
    assert "/api/v1/library" in schema["paths"]
    responses = schema["paths"]["/api/v1/generations/images"]["post"]["responses"]
    assert "202" in responses
    assert responses["401"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ErrorResponse"
    )


def test_cors_uses_configured_origins(test_settings: Settings) -> None:
    application = create_app(test_settings)

    with TestClient(application) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_application_errors_have_a_stable_response(test_settings: Settings) -> None:
    application = create_app(test_settings)

    @application.get("/failure")
    def failure() -> None:
        raise AppError("Invalid operation", code="invalid_operation", status_code=409)

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/failure")

    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "invalid_operation", "message": "Invalid operation"}
    }
