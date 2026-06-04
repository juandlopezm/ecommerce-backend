# Pruebas de rendimiento y estrés (Locust)

Simulan visitantes navegando el catálogo (el caso de mayor tráfico) para medir el comportamiento
del backend bajo carga (RNF-01).

## Requisitos

```bash
pip install -e ".[dev,perf,postgres]"
```

Con el backend corriendo (idealmente contra PostgreSQL, como en producción):

```bash
docker compose up -d db
alembic upgrade head && python -m app.seed && python -m app.seed_products
uvicorn app.main:app --port 8000
```

## Ejecutar

```bash
# Rendimiento: 100 usuarios concurrentes (objetivo RNF-01.3)
locust -f perf/locustfile.py --headless -u 100 -r 20 --run-time 30s --host http://localhost:8000

# Estrés: subir usuarios hasta encontrar el punto de quiebre
locust -f perf/locustfile.py --headless -u 300 -r 50 --run-time 30s --host http://localhost:8000

# Interfaz web (exploratoria, con gráficas)
locust -f perf/locustfile.py --host http://localhost:8000
```

Métricas clave: mediana y percentil 95 de latencia, peticiones/seg (RPS) y % de fallos.

## Hallazgos de las primeras corridas

- A **100 usuarios** el sistema respondió sin fallos, pero el endpoint de **listado** `GET /products`
  mostró una mediana alta (~2.3s), por encima del objetivo RNF-01.2 (<500ms). El detalle de producto
  sí fue rápido (~130ms).
- **Causa probable:** los endpoints son `async` pero ejecutan I/O de base de datos **bloqueante**
  (SQLAlchemy síncrono), lo que serializa las peticiones bajo concurrencia.
- En **estrés alto** (300 usuarios) un único worker de Uvicorn en desarrollo se satura.

## Recomendaciones (tuning para producción)

1. Ejecutar varios workers: `uvicorn app.main:app --workers 4` (o Gunicorn + UvicornWorker).
2. Para el I/O bloqueante: declarar los endpoints de BD como `def` (se ejecutan en threadpool) **o**
   migrar a SQLAlchemy async; y **ampliar el pool** de conexiones (`pool_size`, `max_overflow`).
3. Añadir caché (Redis) al catálogo, como contempla el documento.
4. Repetir las mediciones tras cada ajuste para comparar (medir → ajustar → volver a medir).
