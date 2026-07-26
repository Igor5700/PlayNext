"""Payment gateway port.

The application depends on this abstraction, not on Crypto Pay or any concrete
provider. Swapping providers is a matter of writing a new adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from playnext.core.money import Money
from playnext.domain.enums import PaymentStatus


@dataclass(frozen=True, slots=True)
class GatewayPayment:
    """What a gateway returns after creating / polling a payment."""

    provider_payment_id: str
    status: PaymentStatus
    confirmation_url: str | None = None


class PaymentGateway(Protocol):
    name: str

    async def create_payment(
        self,
        *,
        amount: Money,
        description: str,
        idempotence_key: str,
    ) -> GatewayPayment: ...

    async def get_payment(self, provider_payment_id: str) -> GatewayPayment: ...
