# Tale Star Backend

API y worker local para Tale Star. Es un monolito modular con `CreativeAuthoring`, `GenerativeMedia`, `ContentLibrary` e `IdentityAccess`; aplica DDD y Ports & Adapters, FastAPI, SQLAlchemy 2, Alembic y SQLite WAL. Los cuentos son escritos por el usuario. Las imágenes y la música se guardan como archivos locales; el modo fake permite desarrollar sin GPU.

## Desarrollo local

Requisitos: Windows, Python 3.12 y Git. Desde PowerShell en la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Revisa `.env` antes de iniciar. Para desarrollo local se puede usar el valor JWT de ejemplo; configura un secreto aleatorio propio para cualquier entorno compartido. Las bases, archivos, modelos y cachés se configuran con `DATABASE_URL`, `MEDIA_DIRECTORY`, `MODEL_CACHE_DIRECTORY` y `ASSETS_DIRECTORY`; los pesos no se guardan en Git. CORS acepta por defecto `http://localhost:5173` y `http://127.0.0.1:5173`, configurable mediante `CORS_ORIGINS`.

Aplica las migraciones y levanta API y worker en terminales separadas, con el entorno virtual activo en ambas:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

```powershell
python -m worker
```

El worker atiende una cola persistida en SQLite y procesa un trabajo por vez. API y worker deben compartir `DATABASE_URL`, `MEDIA_DIRECTORY` y `GPU_QUEUE_LOCK_PATH`. La API sirve los assets únicamente al usuario propietario.

Con la API y el worker activos, registra una vez `talestar.smoke@example.com` (contraseña `TaleStar-smoke-test-only-2026!`) en `/api/v1/auth/register`, y abre `http://127.0.0.1:8000/smoke-test`. La página usa payloads fijos, inicia sesión con esa cuenta local de prueba y utiliza los adapters configurados en el worker. Agrega `?run=both` para disparar automáticamente los mismos dos botones durante un smoke test. La ruta está disponible solo en `local` y `test`.

## Generadores

El modo predeterminado usa fakes: `IMAGE_GENERATOR=fake` y `MUSIC_GENERATOR=fake`. Es suficiente para generar archivos de prueba y recorrer el flujo completo sin descargar pesos.

Para Z-Image-Turbo, prepara en el entorno local una instalación de PyTorch compatible con la GPU y ejecuta:

```powershell
python -m pip install -e ".[zimage]"
```

Configura `IMAGE_GENERATOR=zimage`, `ZIMAGE_MODEL_PATH` con una carpeta local o el identificador del modelo y `MODEL_CACHE_DIRECTORY` fuera de Git. Las descargas están desactivadas con `MODEL_DOWNLOADS_ENABLED=false`; habilítalas solo si deseas que Diffusers descargue el modelo. `ZIMAGE_DEVICE`, `ZIMAGE_DTYPE` y `ZIMAGE_CPU_OFFLOAD` seleccionan dispositivo, precisión y offload. La generación real puede requerir bastante memoria.

Para ACE-Step 1.5 Turbo, instala ACE-Step y sus checkpoints según las instrucciones de su proyecto oficial en una ubicación local externa al repositorio. Ejecuta Tale Star en el mismo entorno Python, define `MUSIC_GENERATOR=acestep`, `ACESTEP_PROJECT_ROOT` y `ACESTEP_MODEL_CONFIG=acestep-v15-turbo`, y configura su caché con `MODEL_CACHE_DIRECTORY`. No se usa Language Model ni thinking; Tale Star construye caption y letras a partir de la solicitud. `ACESTEP_DEVICE`, `ACESTEP_OFFLOAD_TO_CPU`, `ACESTEP_OFFLOAD_DIT_TO_CPU` y `ACESTEP_QUANTIZATION` controlan las opciones disponibles del runtime.

Usa un solo worker para la GPU. Workers locales comparten el bloqueo `GPU_QUEUE_LOCK_PATH`; al cambiar el tipo de trabajo, el runtime descarga el modelo activo antes de cargar el otro. Mantener fake mode en la API y activar el modelo solo en el worker evita inicializar los modelos en el proceso HTTP.

## Endpoints para el frontend

Salvo health, los endpoints requieren `Authorization: Bearer <access_token>`.

- Identidad: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `PUT /api/v1/auth/parental-pin`, `POST /api/v1/auth/parental-pin/validate`.
- Personajes, escenarios y estilos: `POST/GET /api/v1/characters`, `GET/PATCH/DELETE /api/v1/characters/{id}`; los mismos métodos para `/scenarios` y `/style-profiles`.
- Cuentos: `POST/GET /api/v1/stories`, `GET/PATCH/DELETE /api/v1/stories/{id}`. Páginas: `POST/GET /api/v1/stories/{story_id}/pages`, `GET/PATCH/DELETE /api/v1/stories/{story_id}/pages/{page_id}`.
- Biblioteca: `POST/GET /api/v1/library`, `GET/PATCH/DELETE /api/v1/library/{id}`. El listado admite `type=image|story|music`, `q=` y `favorite=true|false`; PATCH cambia nombre, descripción o favorito.
- Generación asíncrona: `POST /api/v1/generations/images`, `POST /api/v1/generations/music` (responden 202), `GET /api/v1/generations/{job_id}`.
- Assets: `GET /api/v1/media/assets/{asset_id}` resuelve el ID del asset sin exponer paths locales. Se conserva `GET /api/v1/media/{ruta_relativa}` por compatibilidad; la biblioteca devuelve URLs por ID para imágenes y música.
- Salud: `GET /health` y `GET /api/v1/health`.

Los errores siguen el formato `{"error":{"code":"...","message":"..."}}`. La validación devuelve detalles `loc`, `type` y `msg` sin repetir los valores enviados.

## Migraciones y checks

```powershell
alembic upgrade head
pytest
ruff check .
mypy app
```

Los tests regulares usan adapters fake. `tests/integration` contiene pruebas reales opcionales; requieren modelos instalados/configurados y `RUN_REAL_MODEL_INTEGRATION=1`. Las pruebas no descargan pesos automáticamente. AR y su renderizado pertenecen a Flutter/on-device; el backend entrega las páginas del cuento y los assets.
