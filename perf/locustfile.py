"""Pruebas de rendimiento y estrés con Locust (RNF-01).

Simula múltiples tipos de usuarios navegando el catálogo, autenticándose,
comprando y consultando pedidos (escenarios realistas de e-commerce).

Uso (con el backend corriendo en http://localhost:8000):

    # Rendimiento: 100 usuarios concurrentes durante 60s (RNF-01.3)
    locust -f perf/locustfile.py --headless -u 100 -r 20 --run-time 60s \
        --host http://localhost:8000

    # Estrés: subir usuarios hasta degradar (p. ej. 500)
    locust -f perf/locustfile.py --headless -u 500 -r 50 --run-time 60s \
        --host http://localhost:8000

    # Interfaz web (exploratoria con gráficas):
    locust -f perf/locustfile.py --host http://localhost:8000

    # Prueba de checkout intenso (100% simulan compras)
    locust -f perf/locustfile.py::Comprador --headless -u 50 -r 10 \
        --run-time 60s --host http://localhost:8000
"""

import random
import json
from locust import HttpUser, between, task, events, constant


class VisitanteTienda(HttpUser):
    """Cliente anónimo que explora el catálogo (caso de mayor tráfico)."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
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
            self.client.get(
                f"/api/v1/products/{product_id}",
                name="/api/v1/products/[id]"
            )

    @task(1)
    def filtrar_por_categoria(self) -> None:
        categories = ["Maquillaje", "Skincare", "Fragancia", "Tratamiento"]
        category = random.choice(categories)
        self.client.get(
            f"/api/v1/products?category={category}",
            name="/api/v1/products?category=[name]"
        )

    @task(1)
    def filtrar_por_marca(self) -> None:
        brands = ["Marca A", "Marca B", "Marca C"]
        brand = random.choice(brands)
        self.client.get(
            f"/api/v1/products?brand={brand}",
            name="/api/v1/products?brand=[name]"
        )

    @task(1)
    def health_check(self) -> None:
        self.client.get("/health")


class Comprador(HttpUser):
    """Cliente que realiza compras (checkout flow)."""

    wait_time = between(2, 5)

    def on_start(self) -> None:
        self.product_ids: list[int] = []
        self.products: dict = {}
        resp = self.client.get("/api/v1/products")
        if resp.ok:
            products = resp.json()
            self.product_ids = [p["id"] for p in products]
            for p in products:
                self.products[p["id"]] = p

    @task(1)
    def explorar_productos(self) -> None:
        """Navega el catálogo antes de comprar."""
        self.client.get("/api/v1/products")

    @task(2)
    def ver_detalles_producto(self) -> None:
        """Revisa detalles de productos candidatos."""
        if self.product_ids:
            product_id = random.choice(self.product_ids)
            self.client.get(
                f"/api/v1/products/{product_id}",
                name="/api/v1/products/[id]"
            )

    @task(3)
    def realizar_compra(self) -> None:
        """Completa el flujo de checkout como usuario anónimo."""
        if not self.product_ids:
            return

        product_id = random.choice(self.product_ids)
        product = self.products.get(product_id, {})
        
        order_data = {
            "customer_name": f"Cliente {random.randint(1000, 9999)}",
            "customer_email": f"cliente{random.randint(1000, 9999)}@example.com",
            "items": [
                {
                    "product_id": product_id,
                    "quantity": random.randint(1, 3)
                }
            ],
            "shipping_address": "Calle Falsa 123",
            "payment_method": random.choice(["pasarela", "contra_entrega"])
        }

        resp = self.client.post(
            "/api/v1/orders",
            json=order_data,
            name="/api/v1/orders"
        )
        
        if resp.ok:
            order_id = resp.json().get("id")
            if order_id:
                # Simula que el cliente consulta su pedido
                self.client.get(
                    f"/api/v1/orders/{order_id}",
                    name="/api/v1/orders/[id]"
                )


class UsuarioAutenticado(HttpUser):
    """Cliente autenticado (simula administrador o usuario registrado)."""

    wait_time = constant(2)
    
    def on_start(self) -> None:
        """Autentica el usuario al iniciar."""
        self.token: str = ""
        self.product_ids: list[int] = []
        
        # Intenta login
        login_data = {
            "username": "admin@ecommerce.com",
            "password": "Admin123!"
        }
        
        resp = self.client.post(
            "/api/v1/auth/login",
            data=login_data,
            name="/api/v1/auth/login"
        )
        
        if resp.ok:
            self.token = resp.json().get("access_token", "")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Carga productos
        resp = self.client.get("/api/v1/products")
        if resp.ok:
            self.product_ids = [p["id"] for p in resp.json()]

    @task(1)
    def obtener_usuario_actual(self) -> None:
        """Obtiene datos del usuario autenticado."""
        self.client.get("/api/v1/auth/me")

    @task(2)
    def listar_pedidos_admin(self) -> None:
        """Admin lista todos los pedidos."""
        self.client.get("/api/v1/admin/orders")

    @task(1)
    def ver_bajo_stock(self) -> None:
        """Admin verifica productos con bajo stock."""
        self.client.get("/api/v1/admin/products/low-stock")

    @task(2)
    def crear_producto(self) -> None:
        """Admin intenta crear un producto."""
        product_data = {
            "name": f"Producto Test {random.randint(1000, 9999)}",
            "description": "Descripción de prueba de rendimiento",
            "price": round(random.uniform(10, 200), 2),
            "brand": random.choice(["Marca A", "Marca B", "Marca C"]),
            "category": random.choice(["Maquillaje", "Skincare", "Fragancia"]),
            "stock": random.randint(5, 100)
        }
        
        self.client.post(
            "/api/v1/products",
            json=product_data,
            name="/api/v1/products [POST]"
        )

    @task(1)
    def actualizar_producto(self) -> None:
        """Admin actualiza un producto existente."""
        if self.product_ids:
            product_id = random.choice(self.product_ids)
            update_data = {
                "price": round(random.uniform(10, 200), 2),
                "stock": random.randint(5, 100)
            }
            
            self.client.put(
                f"/api/v1/products/{product_id}",
                json=update_data,
                name="/api/v1/products/[id] [PUT]"
            )

    @task(1)
    def cambiar_estado_pedido(self) -> None:
        """Admin cambia el estado de un pedido."""
        resp = self.client.get("/api/v1/admin/orders")
        if resp.ok:
            orders = resp.json()
            if orders:
                order_id = random.choice(orders).get("id")
                status_data = {
                    "status": random.choice(["confirmado", "enviado", "cancelado"])
                }
                self.client.patch(
                    f"/api/v1/admin/orders/{order_id}/status",
                    json=status_data,
                    name="/api/v1/admin/orders/[id]/status"
                )


class VistazoRapido(HttpUser):
    """Cliente que hace búsquedas rápidas (mobile-like, sin esperar)."""

    wait_time = between(0.5, 1.5)
    
    @task(5)
    def buscar_categoria(self) -> None:
        """Búsquedas rápidas de categorías."""
        categories = ["Maquillaje", "Skincare", "Fragancia"]
        for category in categories:
            self.client.get(
                f"/api/v1/products?category={category}",
                name="/api/v1/products?category=[fast]"
            )

    @task(3)
    def listar_todos(self) -> None:
        """Lista completa rapidamente."""
        self.client.get("/api/v1/products")

    @task(2)
    def health(self) -> None:
        self.client.get("/health")
