# Auditoría técnica breve

- Docker Desktop/containerd presentó errores `read-only`, I/O y snapshotter; se reparó y el almacenamiento pesado quedó en `E:\Docker\Data`.
- El primer build del worker falló al extraer cuBLAS durante la corrupción del daemon. Tras reparar Docker, el build CUDA terminó correctamente.
- Z-Image agotó la memoria WSL; se asignaron 20 GB de RAM y 8 GB de swap en E:. La prueba real posterior pasó.
- ACE-Step 1.5 Turbo: FLAC, `vocal_language` (`en`/`es`), `thinking=false`, batch 1, 8 pasos y shift 3.0. Caption y lyrics son deterministas, sin LLM adicional.
- Diffusers 0.37.1: `ZImagePipeline` usa `torch_dtype`; Z-Image Turbo corre con 8 pasos y BF16. Pesos y caches quedan fuera del repositorio e imágenes.
- Docker validó API CPU, worker CUDA y RTX 3060; ACE-Step y Z-Image generaron assets reales que llegaron a Succeeded y se sirvieron por Media.
- Mantener SQLite WAL/foreign keys en el adaptador SQLAlchemy, condicionado a SQLite; `DATABASE_URL` es configurable. El dominio y los casos de uso no deben conocer SQL ni filesystem.
- Toda lectura y escritura de assets pasa por `AssetStorage`; `LocalAssetStorage` valida rutas/ownership. Adaptadores futuros de object storage no deben cambiar casos de uso.
- Mantener jobs con claim atómico, bloqueo GPU inter-process y un solo runtime de modelo activo. Tests normales usan fake adapters; nunca descargar modelos en pytest.
- Preservar separación de bounded contexts, UUID, ownership por usuario y texto de cuentos escrito por el usuario. Secretos, `.env`, modelos, caches, DB local y medios generados no se versionan.
