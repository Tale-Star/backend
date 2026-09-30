"""Import SQLAlchemy models so the shared metadata knows every mapped table."""

from importlib import import_module

_MODEL_MODULES = (
    "app.identity_access.infrastructure.user_model",
    "app.generative_media.infrastructure.generation_job_model",
    "app.creative_authoring.infrastructure.models",
    "app.content_library.infrastructure.models",
)


def register_models() -> None:
    """Register all bounded-context mappings before using the shared metadata."""
    for module_name in _MODEL_MODULES:
        import_module(module_name)
