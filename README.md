# Tale Star Backend

Backend for Tale Star, an educational platform for creating and managing illustrated stories, images, and music with generative AI.

## Technologies

- Python 3.12
- FastAPI
- SQLAlchemy 2
- Alembic
- SQLite WAL
- PyTorch and Diffusers
- Z-Image-Turbo
- ACE-Step 1.5 Turbo
- Pytest, Ruff, Mypy

## API

### Health

- `GET /health`
- `GET /api/v1/health`

### Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `PUT /api/v1/auth/parental-pin`
- `POST /api/v1/auth/parental-pin/validate`

### Creative Authoring

- `POST/GET /api/v1/characters`
- `GET/PATCH/DELETE /api/v1/characters/{item_id}`
- `POST/GET /api/v1/scenarios`
- `GET/PATCH/DELETE /api/v1/scenarios/{item_id}`
- `POST/GET /api/v1/style-profiles`
- `GET/PATCH/DELETE /api/v1/style-profiles/{item_id}`
- `POST/GET /api/v1/stories`
- `GET/PATCH/DELETE /api/v1/stories/{story_id}`
- `POST/GET /api/v1/stories/{story_id}/pages`
- `GET/PATCH/DELETE /api/v1/stories/{story_id}/pages/{page_id}`

### Generative Media

- `POST /api/v1/generations/images`
- `POST /api/v1/generations/music`
- `GET /api/v1/generations/{job_id}`

### Content Library

- `POST/GET /api/v1/library`
- `GET/PATCH/DELETE /api/v1/library/{item_id}`

### Media

- `GET /api/v1/media/assets/{asset_id}`
- `GET /api/v1/media/{asset_key}`

## Local API documentation

- `http://<host>:<port>/docs` - Swagger UI
- `http://<host>:<port>/redoc` - ReDoc
- `http://<host>:<port>/openapi.json` - OpenAPI schema