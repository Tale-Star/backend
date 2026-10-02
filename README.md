# Tale Star Backend

Backend de Tale Star, plataforma educativa para crear cuentos ilustrados y gestionar imágenes y música generadas con IA.

## Technologies

Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · SQLite WAL · Docker · Docker Compose · PyTorch · CUDA · Diffusers · Z-Image-Turbo · ACE-Step 1.5 · Pytest · Ruff · Mypy

## API

- Health: `GET /health`, `GET /api/v1/health`
- Authentication: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `PUT /api/v1/auth/parental-pin`, `POST /api/v1/auth/parental-pin/validate`
- Creative Authoring: `POST/GET` `/api/v1/characters`, `/api/v1/scenarios`, `/api/v1/style-profiles`, `/api/v1/stories`; `GET/PATCH/DELETE` on their item routes.
- Story Pages: `POST/GET /api/v1/stories/{story_id}/pages`; `GET/PATCH/DELETE /api/v1/stories/{story_id}/pages/{page_id}`
- Generative Media: `POST /api/v1/generations/images`, `POST /api/v1/generations/music`, `GET /api/v1/generations/{job_id}`
- Content Library: `GET/POST /api/v1/library`, `GET/PATCH/DELETE /api/v1/library/{item_id}`
- Media: `GET /api/v1/media/assets/{asset_id}`, `GET /api/v1/media/{asset_key}`

## Local API documentation

- `http://<host>:<port>/docs` — Swagger UI
- `http://<host>:<port>/redoc` — ReDoc
- `http://<host>:<port>/openapi.json` — OpenAPI schema

## Docker

```sh
docker compose build
docker compose run --rm api alembic upgrade head
docker compose up
```

## Model weights

The repository contains model configuration and verified download metadata only. Do not commit
model weights. Copy `.env.example` to `.env` and set `ACESTEP_PROJECT_ROOT` to an installed
ACE-Step 1.5 source checkout. On the first generation, the worker downloads the selected ACE-Step
1.5 Turbo checkpoint, its 5 Hz language model, the Qwen3 0.6B embedder, and VAE into the Hugging
Face cache. Z-Image-Turbo is fetched by Diffusers on the first image generation. Selected LoRAs
are fetched on demand and SHA-256 checked before use.

The three registered profiles are `Flat Anime Style`, `Amelicart Illustration`, and `Flat Color`.
Create a Tale Star StyleProfile with one of these names to select that LoRA from the UI. Its
`visual_settings` may override `zimage_lora_asset` (`flat_anime_style_zit`,
`amelicart_illustration`, or `flat_color_zimage_base`) and `zimage_lora_scale` (0 through 2).
The configured cache, LoRA directory, and ACE-Step checkpoint directory are outside this
checkout by default. A local copy in the Tale Star workspace is reused after checksum validation.

To prefetch ACE-Step checkpoints and the registered LoRAs before the first generation, run from this directory:

```sh
python -m scripts.download_models
```

The ACE-Step prefetch needs several gigabytes of disk space and an internet connection.
Z-Image-Turbo and its translation model are fetched lazily by their adapters. You may set
`MODEL_DOWNLOADS_ENABLED=false` to require all weights to be preloaded. The prompt translator
`Helsinki-NLP/opus-mt-es-en` is fetched only when a Spanish image prompt needs translation; it
runs on CPU. Character `@mentions` are resolved against the authenticated user's stored
characters before a generation job is queued, so the saved job contains the actual character
descriptions rather than only their names.
