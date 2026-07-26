"""Wallet top-ups via one of several configured payment gateways.

Design notes:
- Multiple gateways can be active at once (e.g. "demo" and "crypto_pay") — the
  caller picks one by name per top-up; `Payment.provider` records which.
- Network calls to the gateway happen **outside** DB transactions, so we never
  hold a Postgres transaction open across the wire.
- Crediting is guarded by `payments.mark_succeeded`, which transitions
  PENDING -> SUCCEEDED exactly once. This makes "Check payment" idempotent and
  closes the double-credit hole from the previous implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from playnext.application.ports.payment_gateway import PaymentGateway
from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.core.money import Money
from playnext.domain.enums import PaymentStatus, WalletTxnType
from playnext.domain.errors import OrderNotFound

MIN_TOPUP = Money.from_major(10)
MAX_TOPUP = Money.from_major(100_000)


@dataclass(frozen=True, slots=True)
class TopUpTicket:
    payment_id: int
    confirmation_url: str | None
    amount: Money


class PaymentService:
    def __init__(self, uow: UnitOfWorkFactory, *, gateways: dict[str, PaymentGateway]) -> None:
        self._uow = uow
        self._gateways = gateways

    def available_providers(self) -> list[str]:
        return list(self._gateways)

    async def create_topup(self, user_id: int, amount: Money, *, provider: str) -> TopUpTicket:
        gateway = self._gateways[provider]
        async with self._uow() as uow:
            payment_id = await uow.payments.create(
                user_id=user_id, provider=gateway.name, amount=amount
            )
            await uow.commit()

        gw = await gateway.create_payment(
            amount=amount,
            description=f"Пополнение баланса PlayNext #{payment_id}",
            idempotence_key=f"topup-{payment_id}",
        )

        async with self._uow() as uow:
            await uow.payments.attach_provider(
                payment_id,
                provider_payment_id=gw.provider_payment_id,
                confirmation_url=gw.confirmation_url,
            )
            await uow.commit()

        return TopUpTicket(payment_id, gw.confirmation_url, amount)

    async def cancel_topup(self, user_id: int, payment_id: int) -> None:
        async with self._uow() as uow:
            row = await uow.payments.get(payment_id)
            if row is None or row.user_id != user_id:
                return
            if row.status == PaymentStatus.PENDING.value:
                await uow.payments.set_status_by_id(payment_id, PaymentStatus.CANCELLED.value)
                await uow.commit()

    async def check_topup(self, user_id: int, payment_id: int) -> PaymentStatus:
        async with self._uow() as uow:
            row = await uow.payments.get(payment_id)
            if row is None or row.user_id != user_id:
                raise OrderNotFound(user_message="Платёж не найден.")
            provider_payment_id = row.provider_payment_id
            amount = row.amount
            status = row.status
            provider = row.provider

        if status == PaymentStatus.SUCCEEDED.value:
            return PaymentStatus.SUCCEEDED
        if provider_payment_id is None:
            return PaymentStatus.PENDING

        gateway = self._gateways[provider]
        gw = await gateway.get_payment(provider_payment_id)

        if gw.status is PaymentStatus.SUCCEEDED:
            note = "Demo payment" if gateway.name == "demo" else None
            async with self._uow() as uow:
                if await uow.payments.mark_succeeded(payment_id):
                    await uow.wallet.apply(
                        user_id, type=WalletTxnType.TOPUP, amount=amount, note=note
                    )
                await uow.commit()
        elif gw.status in (PaymentStatus.CANCELLED, PaymentStatus.EXPIRED):
            async with self._uow() as uow:
                await uow.payments.set_status_by_id(payment_id, gw.status.value)
                await uow.commit()

        return gw.status
