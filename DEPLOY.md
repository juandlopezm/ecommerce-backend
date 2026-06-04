# Despliegue gratis — Backend (Render) + PostgreSQL (Neon)

El frontend se despliega aparte en Vercel (ver `ecommerce-frontend/DEPLOY.md`).

## 1. Base de datos: Neon (gratis y persistente)

1. Crea una cuenta en <https://neon.tech> y un proyecto nuevo.
2. Copia la **connection string**. Neon la da así:
   `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`
3. **Cambia el prefijo** a `postgresql+psycopg://` (el driver que usa la app):
   `postgresql+psycopg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`
   Esa es tu `DATABASE_URL`.

## 2. Backend: Render (gratis)

1. Crea cuenta en <https://render.com> y conecta tu GitHub.
2. **New > Blueprint** y selecciona el repo `ecommerce-backend` (usa el `render.yaml` incluido).
   - O bien **New > Web Service** manual con:
     - Build: `pip install -e ".[postgres]"`
     - Start: `alembic upgrade head && python -m app.seed && python -m app.seed_products && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Configura las **variables de entorno** (las marcadas `sync: false`):
   - `DATABASE_URL` → la de Neon (con `+psycopg`).
   - `CORS_ORIGINS` → JSON con la URL del frontend, p. ej. `["https://tu-frontend.vercel.app"]`
     (al inicio puedes poner `["http://localhost:5173"]` y actualizarla cuando tengas la URL de Vercel).
   - `ADMIN_PASSWORD` → una contraseña fuerte para el admin.
   - `JWT_SECRET` lo genera Render automáticamente.
4. Deploy. Cuando termine, tu API estará en `https://ecommerce-backend-xxxx.onrender.com`
   (docs en `/docs`). Pruébala: `GET /health`.

> Nota: el plan **free de Render duerme** tras ~15 min de inactividad; la primera petición tras
> dormir tarda ~30-60s en responder. Es normal para una demo.

## 3. Conectar con el frontend

- En Vercel, define `VITE_API_URL = https://ecommerce-backend-xxxx.onrender.com/api/v1`.
- En Render, asegúrate de que `CORS_ORIGINS` incluya la URL final del frontend en Vercel y redepliega.

## Orden recomendado

1. Neon (BD) → obtén `DATABASE_URL`.
2. Render (backend) → obtén la URL del backend.
3. Vercel (frontend) con `VITE_API_URL` → obtén la URL del frontend.
4. Actualiza `CORS_ORIGINS` en Render con la URL de Vercel y redepliega.
