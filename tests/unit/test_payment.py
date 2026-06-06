"""Pruebas unitarias del procesamiento de pagos (Strategy + Factory)."""

from decimal import Decimal

import pytest

from app.application.services.payment import (
    CashOnDeliveryPayment,
    GatewayPayment,
    get_payment_strategy,
)
from app.domain.entities.order import PaymentMethod, PaymentStatus

TOTAL = Decimal("100000")


def test_gateway_approves_in_sandbox() -> None:
    assert GatewayPayment().process(TOTAL, simulate_failure=False) == PaymentStatus.APROBADO


def test_gateway_rejects_when_simulated() -> None:
    assert GatewayPayment().process(TOTAL, simulate_failure=True) == PaymentStatus.RECHAZADO


def test_cash_on_delivery_is_pending() -> None:
    assert CashOnDeliveryPayment().process(TOTAL, simulate_failure=False) == PaymentStatus.PENDIENTE


def test_factory_returns_gateway_for_pasarela() -> None:
    assert isinstance(get_payment_strategy(PaymentMethod.PASARELA), GatewayPayment)


def test_factory_returns_cod_for_contra_entrega() -> None:
    assert isinstance(get_payment_strategy(PaymentMethod.CONTRA_ENTREGA), CashOnDeliveryPayment)


def test_gateway_negative_amount():
    with pytest.raises(ValueError):
        GatewayPayment().process(Decimal("-100"), False)


def test_cash_on_delivery_negative_amount_raises() -> None:
    # _validate_total también aplica a contra entrega (rama total < 0 -> ValueError).
    with pytest.raises(ValueError):
        CashOnDeliveryPayment().process(Decimal("-1"), simulate_failure=False)


def test_payment_accepts_zero_total_boundary() -> None:
    # Borde: total == 0 es válido (>= 0), no lanza; la pasarela aprueba.
    assert GatewayPayment().process(Decimal("0"), simulate_failure=False) == PaymentStatus.APROBADO


def test_cash_on_delivery_ignores_simulate_failure() -> None:
    # Contra entrega siempre queda PENDIENTE, aunque se pida simular un rechazo.
    result = CashOnDeliveryPayment().process(Decimal("100"), simulate_failure=True)
    assert result == PaymentStatus.PENDIENTE
