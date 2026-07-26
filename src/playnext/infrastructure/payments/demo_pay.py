"""Demo payment gateway — every "payment" succeeds instantly, no real money or
external service involved. Used to let anyone try the full purchase flow
without a live Crypto Pay account. Enabled via PAYMENT_PROVIDER=demo.
"""

from __future__ import annotations

from playnext.application.ports.payment_gateway import GatewayPayment
from playnext.core.money import Money
from playnext.domain.enums import PaymentStatus


class DemoPaymentGateway:
    name = "demo"

    async def create_payment(
        self, *, amount: Money, description: str, idempotence_key: str
    ) -> GatewayPayment:
        return GatewayPayment(
            provider_payment_id=idempotence_key,
            status=PaymentStatus.SUCCEEDED,
            confirmation_url=None,
        )

    async def get_payment(self, provider_payment_id: str) -> GatewayPayment:
        return GatewayPayment(
            provider_payment_id=provider_payment_id, status=PaymentStatus.SUCCEEDED
        )
