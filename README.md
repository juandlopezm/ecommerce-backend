# ecommerce-backend

API REST del e-commerce de productos de belleza (MVP). Backend desacoplado consumido por los clientes
web y móvil. Construido siguiendo la especificación de `ESP.docx`.

## Stack

- **Python 3.12 + FastAPI** — API REST asíncrona con documentación automática (OpenAPI).
- **SQLAlchemy 2.0 + Alembic** — acceso a datos y migraciones.
- **Pydantic v2** — validación y serialización.
- **PostgreSQL** — almacenamiento transaccional.
- **JWT (OAuth2) + passlib[bcrypt]** — autenticación con tokens y hash seguro de contraseñas.

Arquitectura: **Clean Architecture** (dominio / aplicación / infraestructura) con patrones
**Repository** y **Dependency Injection**.

## Estructura

```
app/
  core/            # config, seguridad (hash/JWT), base de datos
  domain/          # entidades + interfaces de repositorio
  infrastructure/  # modelos SQLAlchemy + repositorios concretos
  application/     # schemas Pydantic + servicios (casos de uso)
  api/             # dependencias + routers/endpoints
migrations/        # Alembic
tests/             # pruebas unitarias e integración (pytest)
```

## Puesta en marcha (desarrollo)

```bash
# 1. Crear entorno e instalar dependencias
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"

# 2. Configurar variables de entorno
copy .env.example .env        # Windows

# 3. Levantar PostgreSQL
docker compose up -d db

# 4. Aplicar migraciones y sembrar el administrador
alembic upgrade head
python -m app.seed

# 5. Ejecutar la API
uvicorn app.main:app --reload
```

Documentación interactiva en `http://localhost:8000/docs`.

## Pruebas QA

```bash
pytest                # ejecuta las pruebas con cobertura (umbral 80%)
ruff check .          # linting
black --check .       # formato
mypy app              # tipos
```

## Autenticación (RF-07)

| Método | Ruta                     | Descripción                                  |
|--------|--------------------------|----------------------------------------------|
| POST   | `/api/v1/auth/register`  | Registro de usuario (rol `cliente`).         |
| POST   | `/api/v1/auth/login`     | Login OAuth2, devuelve JWT (con rate limit). |
| GET    | `/api/v1/auth/me`        | Datos del usuario autenticado.               |
| GET    | `/api/v1/admin/ping`     | Ruta protegida solo para `administrador`.    |

## Git Flow

- `main` — releases estables.
- `develop` — integración.
- `feature/*` — desarrollo de funcionalidades (p. ej. `feature/auth-login`).
