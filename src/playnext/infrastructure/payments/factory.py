"""Build every payment gateway available to the running bot.

Demo is always on (instant, free top-ups). Crypto Pay is added alongside it
whenever a token is configured — both coexist, the user picks per top-up.
"""

from __future__ import annotations

from playnext.application.ports.payment_gateway import PaymentGateway
from playnext.core.config import Settings
from playnext.infrastructure.payments.crypto_pay import CryptoPayGateway
from playnext.infrastructure.payments.demo_pay import DemoPaymentGateway


def build_gateways(settings: Settings) -> dict[str, PaymentGateway]:
    gateways: dict[str, PaymentGateway] = {"demo": DemoPaymentGateway()}
    if settings.crypto_pay_token:
        gateways["crypto_pay"] = CryptoPayGateway(
            api_token=settings.crypto_pay_token,
            testnet=settings.crypto_pay_testnet,
        )
    return gateways
