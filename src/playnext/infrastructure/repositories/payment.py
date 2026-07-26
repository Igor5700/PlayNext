"""Payment repository (external top-up records)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from playnext.core.money import Money
from playnext.domain.enums import PaymentStatus
from playnext.infrastructure.db.models import PaymentORM

_PENDING = PaymentStatus.PENDING.value
_SUCCEEDED = PaymentStatus.SUCCEEDED.value


@dataclass(frozen=True, slots=True)
class PaymentReadModel:
    id: int
    user_id: int
    provider: str
    provider_payment_id: str | None
    amount: Money
    status: str
    confirmation_url: str | None


class PaymentRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: int, provider: str, amount: Money) -> int:
        row = PaymentORM(
            user_id=user_id, provider=provider, amount_minor=amount.minor, status=_PENDING
        )
        self._session.add(row)
        await self._session.flush()
        return row.id

    async def attach_provider(
        self, payment_id: int, *, provider_payment_id: str, confirmation_url: str | None
    ) -> None:
        row = await self._session.get(PaymentORM, payment_id)
        if row is not None:
            row.provider_payment_id = provider_payment_id
            row.confirmation_url = confirmation_url

    async def get(self, payment_id: int) -> PaymentReadModel | None:
        row = await self._session.get(PaymentORM, payment_id)
        if row is None:
            return None
        return PaymentReadModel(
            id=row.id,
            user_id=row.user_id,
            provider=row.provider,
            provider_payment_id=row.provider_payment_id,
            amount=Money(row.amount_minor),
            status=row.status,
            confirmation_url=row.confirmation_url,
        )

    async def mark_succeeded(self, payment_id: int) -> bool:
        """Atomic PENDING -> SUCCEEDED. Only the first caller gets True."""
        # AsyncSession.execute() is typed generically as Result[Any]; an UPDATE
        # always yields a CursorResult (which has .rowcount) at runtime.
        result = cast(
            "CursorResult[Any]",
            await self._session.execute(
                update(PaymentORM)
                .where(PaymentORM.id == payment_id, PaymentORM.status == _PENDING)
                .values(status=_SUCCEEDED)
            ),
        )
        return bool(result.rowcount)

    async def set_status_by_id(self, payment_id: int, status: str) -> None:
        row = await self._session.get(PaymentORM, payment_id)
        if row is not None:
            row.status = status

    async def list_recent(self, *, limit: int, offset: int) -> tuple[list[PaymentReadModel], int]:
        total = int(await self._session.scalar(select(func.count(PaymentORM.id))) or 0)
        rows = await self._session.scalars(
            select(PaymentORM).order_by(PaymentORM.id.desc()).limit(limit).offset(offset)
        )
        items = [
            PaymentReadModel(
                id=row.id,
                user_id=row.user_id,
                provider=row.provider,
                provider_payment_id=row.provider_payment_id,
                amount=Money(row.amount_minor),
                status=row.status,
                confirmation_url=row.confirmation_url,
            )
            for row in rows.all()
        ]
        return items, total
