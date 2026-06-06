# Pruebas de rendimiento y estrés (Locust)

Simulan diferentes tipos de usuarios navegando el e-commerce bajo carga (RNF-01).

## 🔄 Ciclo de vida en el Pipeline

### En desarrollo (feature branches)
✅ **No ejecuta** pruebas de rendimiento (optimiza tiempo de feedback)

### En staging (Pull Request a develop/main)
✅ **Ejecuta 4 pruebas automáticamente** en docker-compose:
1. **Rendimiento estándar** (100 visitantes - 60s)
2. **Checkout** (20 compradores - 60s)
3. **Admin CRUD** (15 administradores - 60s)
4. **Estrés combinado** (200 usuarios mixtos - 90s)

**Gate:** P95 ≤ 1500ms | Fallos < 5%

**Acceso a reportes HTML:**
- En GitHub → Actions → Pipeline Backend → (tu PR)
- Descarga artefacto: `cd-perf` 
- Archivos:
  - `index.html` — Inicio con acceso a todos
  - `locust-standard.html` — Reporte detallado visitantes
  - `locust-checkout.html` — Reporte detallado checkout
  - `locust-admin.html` — Reporte detallado admin
  - `locust-stress.html` — Reporte detallado estrés
  - `perf_dashboard.html` — Dashboard consolidado

### En producción (push a main)
✅ **Reutiliza** resultados del PR (no repite pruebas)

---

## 👥 Tipos de usuarios simulados

| Tipo | Descripción | Patrón |
|------|-------------|--------|
| **VisitanteTienda** | Navega catálogo sin autenticarse | Lectura: 3 catálogo, 2 detalle, 1 filtro, 1 health |
| **Comprador** | Compra anónima (checkout flow) | Exploración + 3x compras |
| **UsuarioAutenticado** | Admin CRUD (auth required) | Login + pedidos + productos |
| **VistazoRapido** | Mobile-like (búsquedas rápidas) | 5x categorías, 3x listado, 2x health |

---

## 🏠 Requisitos locales

```bash
# Instalar con soporte perf
pip install -e ".[dev,perf,postgres]"
```

Levantar backend:
```bash
docker compose up -d db
alembic upgrade head
python -m app.seed && python -m app.seed_products
uvicorn app.main:app --port 8000
```

---

## 🚀 Ejecutar pruebas en local

### Opción 1: Script interactivo (Windows)
```powershell
cd perf
.\run_tests.ps1
```
Menú con 8 opciones de prueba.

### Opción 2: Comandos manuales

**1. Rendimiento estándar (100 visitantes, 60s)**
```bash
locust -f perf/locustfile.py::VisitanteTienda --headless -u 100 -r 20 --run-time 60s \
    --host http://localhost:8000 --csv reports/locust-standard --html reports/locust-standard.html
```

**2. Checkout (20 compradores, 60s)**
```bash
locust -f perf/locustfile.py::Comprador --headless -u 20 -r 5 --run-time 60s \
    --host http://localhost:8000 --csv reports/locust-checkout --html reports/locust-checkout.html
```

**3. Admin CRUD (15 administradores, 60s)**
```bash
locust -f perf/locustfile.py::UsuarioAutenticado --headless -u 15 -r 3 --run-time 60s \
    --host http://localhost:8000 --csv reports/locust-admin --html reports/locust-admin.html
```

**4. Estrés (200 usuarios, 90s)**
```bash
locust -f perf/locustfile.py --headless -u 200 -r 40 --run-time 90s \
    --host http://localhost:8000 --csv reports/locust-stress --html reports/locust-stress.html
```

**5. Interfaz web (gráficas en vivo)**
```bash
locust -f perf/locustfile.py --host http://localhost:8000
# Abre http://localhost:8089
```

### Opción 3: Generar dashboard consolidado
```bash
# Después de las 4 pruebas, generar dashboard HTML
python perf/generate_report.py reports reports/perf_dashboard.html
```

---

## 📊 Métricas clave

| Métrica | Descripción | Objetivo |
|---------|-------------|----------|
| **Latencia (mediana)** | Tiempo típico de respuesta | <500ms (lectura) |
| **P95** | 95% de peticiones responden bajo este | <1500ms |
| **RPS** | Peticiones/segundo | >5 RPS |
| **Tasa de fallos** | % de errores | <5% |
| **Throughput** | MB/s transferidos | - |

---

## ✅ Resultados esperados

### 100 usuarios (rendimiento normal)
```
GET /products:              Mediana ~100-200ms  P95 <500ms   Fallos 0%
GET /products/{id}:          Mediana ~50-100ms   P95 <300ms   Fallos 0%
POST /orders (checkout):      Mediana ~30-100ms   P95 <500ms   Fallos 0%
```

### 300+ usuarios (degradación)
- Latencia 3-5x más alta
- P95 puede exceder 1500ms
- Pool de BD se satura

### 500+ usuarios (estrés extremo)
- Un solo worker Uvicorn falla
- Requiere múltiples workers o async

---

## 🔧 Recomendaciones para producción

### 1. Múltiples workers (inmediato)
```bash
# Opción A: Uvicorn con workers
uvicorn app.main:app --workers 4 --port 8000

# Opción B: Gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### 2. SQLAlchemy async (medio plazo)
Migrar endpoints de BD a `async def` + `AsyncSession` para evitar bloqueos.

### 3. Pool de conexiones DB (inmediato)
En `DATABASE_URL`:
```
postgresql+psycopg://user:pass@host/db?pool_size=20&max_overflow=10
```

### 4. Redis caché (medio plazo)
Caché GET /products (lectura pesada):
```python
@cache.cached(timeout=300)
def get_products():
    ...
```

### 5. CDN (si hay assets estáticos)
Servir CSS, JS, imágenes desde CloudFront/Vercel Edge.

### 6. Load balancer (scaling horizontal)
Nginx/HAProxy con múltiples instancias del backend.

---

## 🎯 Workflow de tuning

1. **Medir baseline:**
   ```bash
   locust ... -u 100 -r 20 --run-time 60s --csv reports/baseline
   ```

2. **Implementar mejora** (e.g., agregar workers)

3. **Volver a medir:**
   ```bash
   locust ... -u 100 -r 20 --run-time 60s --csv reports/after
   ```

4. **Comparar:**
   ```python
   import csv
   def compare(baseline, after):
       baseline_p95 = ... # leer CSV
       after_p95 = ...
       diff = (after_p95 - baseline_p95) / baseline_p95 * 100
       print(f"Mejora: {diff:+.1f}%")
   ```

5. **Iterar** hasta cumplir RNF-01

---

## 📁 Archivos

| Archivo | Descripción |
|---------|------------|
| `locustfile.py` | Escenarios con 4 tipos de usuarios |
| `generate_report.py` | Script para dashboard HTML consolidado |
| `run_tests.ps1` | Script PowerShell (menú interactivo Windows) |
| `run_tests.sh` | Script Bash (menú interactivo Linux/Mac) |
| `README.md` | Este archivo |

---

## 🔍 Troubleshooting

**"ConnectionRefusedError"**
- ✓ Verifica que backend corre en http://localhost:8000
- ✓ Prueba: `curl http://localhost:8000/health`

**"P95 supera el límite"**
- ↗️ Incrementar workers: `uvicorn ... --workers 4`
- ↗️ Revisar pool DB: aumentar `pool_size`
- ↗️ Considerar SQLAlchemy async

**"100% fallos en POST /orders"**
- ✓ Stock insuficiente (normal bajo carga)
- ✓ Revisar lógica transaccional en `app/application/order_service.py`

**"Latencia ~2-4s en GET /products"**
- ✓ SQLAlchemy síncrono bloquea el event loop
- ↗️ Opción 1: Cambiar endpoints a `def` (threadpool)
- ↗️ Opción 2: Migrar a SQLAlchemy async
- ↗️ Opción 3: Agregar caché Redis

---

## 📚 Referencias

- [Locust docs](https://docs.locust.io/)
- [FastAPI performance](https://fastapi.tiangolo.com/deployment/concepts/)
- [SQLAlchemy async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [RNF-01 (especificación)](../ESP.docx) — Requisitos no funcionales

---

## 💡 Tips

- Los reportes HTML de Locust son **interactivos** — clickea columnas para ordenar
- En el pipeline, los reportes se guardan **7 días** — descárgalos antes
- Para desarrollo rápido, usa `-u 50 --run-time 30s` (más rápido)
- Compara **siempre con baseline** para detectar regresiones
