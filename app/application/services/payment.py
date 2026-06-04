"""Procesamiento de pagos simulado — patrones Strategy y Factory (RF-05).

Cada método de pago implementa una estrategia que decide el estado del pago. En desarrollo,
la pasarela funciona en modo sandbox (aprueba salvo que se solicite simular un rechazo).
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from app.domain.entities.order import PaymentMethod, PaymentStatus


class PaymentStrategy(ABC):
    """Estrategia de procesamiento de pago."""

    @abstractmethod
    def process(self, total: Decimal, simulate_failure: bool) -> PaymentStatus:
        """Devuelve el estado del pago para el total dado."""


class GatewayPayment(PaymentStrategy):
    """Pasarela en línea (sandbox): aprueba, salvo simulación de rechazo (HU-07/HU-08)."""

    def process(self, total: Decimal, simulate_failure: bool) -> PaymentStatus:
        if simulate_failure:
            return PaymentStatus.RECHAZADO
        return PaymentStatus.APROBADO


class CashOnDeliveryPayment(PaymentStrategy):
    """Contra entrega / transferencia: el pedido queda pendiente de pago (RF-05.2)."""

    def process(self, total: Decimal, simulate_failure: bool) -> PaymentStatus:
        return PaymentStatus.PENDIENTE


def get_payment_strategy(method: PaymentMethod) -> PaymentStrategy:
    """Factory que devuelve la estrategia según el método de pago elegido."""
    strategies: dict[PaymentMethod, PaymentStrategy] = {
        PaymentMethod.PASARELA: GatewayPayment(),
        PaymentMethod.CONTRA_ENTREGA: CashOnDeliveryPayment(),
    }
    return strategies[method]
