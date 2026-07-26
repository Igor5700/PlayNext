"""Promo code repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from playnext.domain.models import PromoCode
from playnext.infrastructure.db.models import PromoCodeORM
from playnext.infrastructure.repositories.mappers import to_promo


class PromoRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, code: str) -> PromoCode | None:
        row = await self._session.get(PromoCodeORM, code)
        return to_promo(row) if row else None

    async def list_all(self) -> list[PromoCode]:
        rows = await self._session.scalars(
            select(PromoCodeORM).order_by(PromoCodeORM.created_at.desc())
        )
        return [to_promo(row) for row in rows.all()]

    async def list_active(self) -> list[PromoCode]:
        # The table is small (admin-managed codes, not a hot path) — filtering
        # "usable in principle" here rather than duplicating that rule in SQL.
        now = datetime.now(UTC)
        return [promo for promo in await self.list_all() if promo.is_available(now=now)]

    async def create(self, promo: PromoCode) -> None:
        self._session.add(
            PromoCodeORM(
                code=promo.code,
                discount_type=promo.discount_type.value,
                value=promo.value,
                is_active=promo.is_active,
                max_uses=promo.max_uses,
                used_count=promo.used_count,
                min_subtotal_minor=promo.min_subtotal.minor,
                valid_until=promo.valid_until,
            )
        )
        await self._session.flush()

    async def increment_uses(self, code: str) -> None:
        row = await self._session.get(PromoCodeORM, code)
        if row is not None:
            row.used_count += 1

    async def set_active(self, code: str, active: bool) -> None:
        row = await self._session.get(PromoCodeORM, code)
        if row is not None:
            row.is_active = active
