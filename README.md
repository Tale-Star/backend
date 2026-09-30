# Tale Star Backend

Backend modular para la plataforma creativa Tale Star. La API ofrece una base para autoría creativa, generación de medios, biblioteca de contenido e identidad y acceso.

## Tecnologías y arquitectura

- Python 3.12 y FastAPI.
- Monolito modular con `CreativeAuthoring`, `GenerativeMedia`, `ContentLibrary` e `IdentityAccess`.
- DDD y Ports & Adapters; CQRS ligero, sin Event Sourcing.
- SQLAlchemy 2 y Alembic; SQLite con WAL para desarrollo local.
- Archivos locales para assets. No se integra aún ningún modelo de IA ni autenticación completa.

## Requisitos e instalación

Requiere Python 3.12. En PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edita `.env` para configurar la URL de base de datos, el directorio de assets y los orígenes CORS. No guardes secretos en Git.

## Migraciones y ejecución

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

La documentación interactiva queda en `/docs`; las rutas de disponibilidad son `/health` y `/api/v1/health`.

## Verificación local

```powershell
pytest
ruff check .
mypy app
```

