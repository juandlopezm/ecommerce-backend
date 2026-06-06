# ecommerce-backend

![CI Backend](https://github.com/juandlopezm/ecommerce-backend/actions/workflows/ci.yml/badge.svg)
![Cobertura](https://raw.githubusercontent.com/juandlopezm/ecommerce-backend/python-coverage-comment-action-data/badge.svg)
[![codecov](https://codecov.io/gh/juandlopezm/ecommerce-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/juandlopezm/ecommerce-backend)

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
pip install -e ".[dev,postgres]"   # 'postgres' instala el driver psycopg para PostgreSQL

# 2. Configurar variables de entorno
copy .env.example .env        # Windows

# 3. Levantar PostgreSQL
docker compose up -d db

# 4. Aplicar migraciones y sembrar el administrador (+ productos de prueba opcionales)
alembic upgrade head
python -m app.seed
python -m app.seed_products   # opcional: 5 productos de prueba en el catálogo

# 5. Ejecutar la API
uvicorn app.main:app --reload
```

Documentación interactiva en `http://localhost:8000/docs`.

## Pruebas QA

Las pruebas están separadas por tipo:

- `tests/unit/` — **unitarias puras** (sin BD): lógica de servicios, seguridad, pagos y entidades
  (usan dobles/fakes de `tests/fakes.py`).
- `tests/integration/` — **integración**: endpoints HTTP, repositorios SQLAlchemy y dependencias
  (usan base de datos real: SQLite en memoria o PostgreSQL si se define `TEST_DATABASE_URL`).

```bash
pytest tests/unit         # solo unitarias (rápido)
pytest                    # suite completa (unit + integración)
ruff check . && black --check . && mypy app
```

El **gate de cobertura ≥ 80%** se aplica en la CI al mergear (no en cada corrida local).

## Integración Continua (CI/CD)

Pipeline en GitHub Actions (`.github/workflows/ci.yml`), por capas:

| Disparador | Qué corre |
|---|---|
| **Cada commit** (local, hook `pre-commit`) | ruff + black + unitarias |
| **Cada push / PR** | `lint` (ruff/black/mypy) + `unit` (unitarias + cobertura) |
| **PR a `develop`/`main` y push a esas ramas** | `integration` = suite completa contra **PostgreSQL** + **gate cobertura ≥ 80%** |

Métricas: artefactos de cobertura (`coverage.xml` + HTML), **comentario de cobertura en el PR**
(py-cov-action), **Codecov**, y un check de tests aprobados/fallidos (test-reporter).

**Criterios de aceptación (branch protection en `develop`/`main`):** para mergear se exige PR y que
pasen `lint`, `unit` e `integration` (cobertura ≥ 80%). Si una prueba falla, se corrige en la rama
`feature/*` y se vuelve a pushear — no se mergea hasta estar en verde.

Hooks locales (una sola vez):

```bash
pip install -e ".[dev]"
pre-commit install        # ahora cada `git commit` corre ruff + black + unitarias
```

## Autenticación (RF-07)

| Método | Ruta                     | Descripción                                  |
|--------|--------------------------|----------------------------------------------|
| POST   | `/api/v1/auth/register`  | Registro de usuario (rol `cliente`).         |
| POST   | `/api/v1/auth/login`     | Login OAuth2, devuelve JWT (con rate limit). |
| GET    | `/api/v1/auth/me`        | Datos del usuario autenticado.               |
| GET    | `/api/v1/admin/ping`     | Ruta protegida solo para `administrador`.    |

## Catálogo de productos (CRUD — RF-01 / RF-08.2)

Lectura pública; la escritura requiere token de `administrador`.

| Método | Ruta                          | Acceso | Descripción                                  |
|--------|-------------------------------|--------|----------------------------------------------|
| GET    | `/api/v1/products`            | Público| Lista productos (filtros `?category=&brand=`).|
| GET    | `/api/v1/products/{id}`       | Público| Detalle de un producto.                      |
| POST   | `/api/v1/products`            | Admin  | Crea un producto.                            |
| PUT    | `/api/v1/products/{id}`       | Admin  | Actualiza un producto (parcial).             |
| DELETE | `/api/v1/products/{id}`       | Admin  | Elimina un producto.                         |

## Pedidos y checkout (RF-04 / RF-05 / RF-06)

Compra como invitado o autenticado; el pago es simulado (Strategy/Factory). El checkout descuenta
stock de forma **atómica** (HU-10).

| Método | Ruta                                   | Acceso | Descripción                                       |
|--------|----------------------------------------|--------|---------------------------------------------------|
| POST   | `/api/v1/orders`                       | Público| Procesa la compra y genera el pedido.             |
| GET    | `/api/v1/orders/{id}`                  | Público| Consulta un pedido (confirmación/seguimiento).    |
| GET    | `/api/v1/admin/orders`                 | Admin  | Lista todos los pedidos.                          |
| PATCH  | `/api/v1/admin/orders/{id}/status`     | Admin  | Cambia el estado (al `cancelado` restaura stock). |
| GET    | `/api/v1/admin/products/low-stock`     | Admin  | Productos con stock bajo o agotado.               |

Métodos de pago: `pasarela` (sandbox, aprueba salvo `simulate_payment_failure`) y `contra_entrega`
(queda `pendiente`). Estados del pedido: `pendiente`, `confirmado`, `enviado`, `cancelado`.

## Git Flow

- `main` — releases estables.
- `develop` — integración.
- `feature/*` — desarrollo de funcionalidades (p. ej. `feature/auth-login`).
