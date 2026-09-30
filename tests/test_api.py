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


def test_docs_and_openapi_are_available_and_root_redirects(test_settings: Settings) -> None:
    application = create_app(test_settings)

    with TestClient(application) as client:
        docs = client.get("/docs")
        redoc = client.get("/redoc")
        openapi = client.get("/openapi.json")
        root = client.get("/", follow_redirects=False)

    assert docs.status_code == 200
    assert "swagger-ui" in docs.text
    assert redoc.status_code == 200
    assert "redoc" in redoc.text.lower()
    assert openapi.status_code == 200
    assert root.status_code == 307
    assert root.headers["location"] == "/docs"
    assert "/docs" not in openapi.json()["paths"]


def test_openapi_lists_frontend_routes_and_consistent_responses(test_settings: Settings) -> None:
    application = create_app(test_settings)

    with TestClient(application) as client:
        schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Tale Star Backend API"
    assert schema["info"]["version"] == "0.1.0"
    assert schema["info"]["description"]
    assert {tag["name"] for tag in schema["tags"]} == {
        "Health",
        "Authentication",
        "Creative Authoring",
        "Generative Media",
        "Content Library",
        "Media",
    }
    assert "/api/v1/library" in schema["paths"]
    assert sum(len(operations) for operations in schema["paths"].values()) == 42
    assert schema["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
    }
    assert schema["paths"]["/api/v1/generations/images"]["post"]["security"] == [{"HTTPBearer": []}]
    assert "security" not in schema["paths"]["/api/v1/auth/login"]["post"]
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
