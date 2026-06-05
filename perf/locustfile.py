"""Pruebas de rendimiento y estrés con Locust (RNF-01).

Simula visitantes navegando el catálogo (lectura), que es el caso de mayor tráfico.

Uso (con el backend corriendo en http://localhost:8000):

    # Rendimiento: 100 usuarios concurrentes durante 30s (RNF-01.3)
    locust -f perf/locustfile.py --headless -u 100 -r 20 --run-time 30s \
        --host http://localhost:8000

    # Estrés: subir usuarios hasta degradar (p. ej. 500)
    locust -f perf/locustfile.py --headless -u 500 -r 50 --run-time 30s \
        --host http://localhost:8000

    # Interfaz web (exploratoria):
    locust -f perf/locustfile.py --host http://localhost:8000
"""

import random

from locust import HttpUser, between, task


class VisitanteTienda(HttpUser):
    """Cliente que explora el catálogo como lo haría un visitante real."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        # Carga inicial del catálogo para conocer ids válidos de producto.
        self.product_ids: list[int] = []
        resp = self.client.get("/api/v1/products")
        if resp.ok:
            self.product_ids = [p["id"] for p in resp.json()]

    @task(3)
    def listar_catalogo(self) -> None:
        self.client.get("/api/v1/products")

    @task(2)
    def ver_detalle(self) -> None:
        if self.product_ids:
            product_id = random.choice(self.product_ids)
            # name agrupa todas las urls /{id} en una sola fila de estadísticas.
            self.client.get(f"/api/v1/products/{product_id}", name="/api/v1/products/[id]")

    @task(1)
    def filtrar_por_categoria(self) -> None:
        self.client.get("/api/v1/products?category=Maquillaje", name="/api/v1/products?category")

    @task(1)
    def health(self) -> None:
        self.client.get("/health")
