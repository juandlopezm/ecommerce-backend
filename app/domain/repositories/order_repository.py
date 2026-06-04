"""Interfaz (puerto) del repositorio de pedidos — patrón Repository."""

from abc import ABC, abstractmethod

from app.domain.entities.order import Order, OrderStatus


class OrderRepository(ABC):
    """Contrato de persistencia de pedidos."""

    @abstractmethod
    def create_checkout(self, order: Order) -> Order:
        """Crea el pedido descontando el stock de forma atómica (RF-02.2 / HU-10).

        Debe bloquear las filas de producto, validar disponibilidad y, si algún ítem no
        tiene stock suficiente, abortar sin persistir nada.
        """

    @abstractmethod
    def get_by_id(self, order_id: int) -> Order | None:
        """Devuelve el pedido con ese id, o ``None`` si no existe."""

    @abstractmethod
    def list(self) -> list[Order]:
        """Lista todos los pedidos (panel de administración, RF-08.6)."""

    @abstractmethod
    def set_status(self, order_id: int, status: OrderStatus) -> Order:
        """Actualiza el estado de un pedido (RF-08.7)."""

    @abstractmethod
    def cancel_and_restore_stock(self, order_id: int) -> Order:
        """Cancela el pedido y restaura el stock de sus productos (RF-02.5)."""
