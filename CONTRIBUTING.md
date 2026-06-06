# Guía de contribución — Git Flow + CI/CD

## Ramas (Git Flow)

- **`main`** — releases estables (producción).
- **`develop`** — integración.
- **`feature/*`** — desarrollo de cada funcionalidad.

Flujo: `feature/*` → **PR a `develop`** → (release) **PR `develop` → `main`**.

## Calidad EN CADA COMMIT (local)

Activa los hooks una sola vez (con el entorno virtual activado):

```bash
pip install -e ".[dev]"
pre-commit install
```

Desde entonces, cada `git commit` corre **ruff + black + unitarias** y **bloquea el commit** si algo
falla.

## Calidad EN CADA PUSH / PR (CI — `.github/workflows/ci.yml`)

| Disparador | Jobs |
|---|---|
| push a cualquier rama y PR | `Lint y tipos` + `Pruebas unitarias` |
| PR a `develop`/`main` y push a esas ramas | + `Integracion y cobertura` (suite completa contra PostgreSQL, **gate ≥ 80%**) |

Métricas: artefactos de cobertura, comentario de cobertura en el PR (py-cov-action), Codecov y check de
resultados (test-reporter).

## Criterios de aceptación (para mergear)

1. `Lint y tipos` en verde (ruff/black/mypy).
2. `Pruebas unitarias` en verde.
3. `Integracion y cobertura` en verde con **cobertura ≥ 80%**.

Si una prueba falla: se corrige en la rama `feature/*` y se vuelve a pushear. **No se mergea en rojo.**

## Activar el BLOQUEO automático (branch protection) — PENDIENTE

> En **repo privado del plan gratuito**, GitHub **no permite** activar branch protection ni rulesets
> (devuelve HTTP 403: "Upgrade to GitHub Pro or make this repository public"). La CI ya marca rojo/verde
> y el gate de cobertura ya falla el check; solo falta el bloqueo que **impida** mergear en rojo.
>
> Actívalo cuando hagas el repo **público** o tengas **GitHub Pro**:

### Opción A — Interfaz (recomendada)

`Settings → Rules → Rulesets → New branch ruleset`:
- **Enforcement:** Active.
- **Target branches:** incluir `develop` y `main`.
- **Rules:**
  - *Require a pull request before merging* (0 aprobaciones).
  - *Require status checks to pass* → agregar: **`Lint y tipos`**, **`Pruebas unitarias`**,
    **`Integracion y cobertura`**; marcar *Require branches to be up to date*.
  - *Block force pushes*.

### Opción B — API (un comando)

```bash
gh api --method POST repos/juandlopezm/ecommerce-backend/rulesets \
  --input .github/ruleset.json
```

(El ruleset listo está en `.github/ruleset.json`.) Lo mismo aplica al repo `ecommerce-frontend` con
sus propios checks de CI.
