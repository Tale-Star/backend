# Auditoría breve

- Mantener explícitos los límites y dependencias entre bounded contexts.
- El dominio permanece Python puro: sin FastAPI, SQLAlchemy ni librerías de IA.
- Cambiar el esquema solo con Alembic; SQLite local debe conservar WAL.
- Usar UUID en identificadores de dominio y no introducir Event Sourcing.
- Leer configuración desde settings y `.env`; nunca versionar secretos.
- No añadir colas, Redis ni autenticación completa hasta que exista un caso de uso.
- Mantener módulos y archivos en `snake_case`, clases en `PascalCase`.

