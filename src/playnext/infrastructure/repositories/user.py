"""User and wallet repositories."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from playnext.core.money import Money
from playnext.domain.enums import WalletTxnType
from playnext.domain.errors import InsufficientBalance
from playnext.domain.models import User, WalletTransaction
from playnext.infrastructure.db.models import UserORM, WalletTransactionORM
from playnext.infrastructure.repositories.mappers import to_user, to_wallet_txn


class UserRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> User | None:
        row = await self._session.get(UserORM, user_id)
        return to_user(row) if row else None

    async def get_or_create(self, user_id: int, *, username: str | None, first_name: str) -> User:
        row = await self._session.get(UserORM, user_id)
        if row is None:
            row = UserORM(id=user_id, username=username, first_name=first_name, balance_minor=0)
            self._session.add(row)
            await self._session.flush()
        else:
            # Only touch the row when contact info actually changed (avoids a
            # needless UPDATE on every single interaction).
            if row.username != username:
                row.username = username
            if row.first_name != first_name:
                row.first_name = first_name
        return to_user(row)

    async def set_blocked(self, user_id: int, blocked: bool) -> None:
        row = await self._session.get(UserORM, user_id)
        if row is not None:
            row.is_blocked = blocked

    async def all_ids(self) -> list[int]:
        result = await self._session.scalars(
            select(UserORM.id).where(UserORM.is_blocked.is_(False))
        )
        return list(result.all())

    async def count(self) -> int:
        return int(await self._session.scalar(select(func.count(UserORM.id))) or 0)

    async def list_recent(self, *, limit: int, offset: int) -> list[User]:
        result = await self._session.scalars(
            select(UserORM).order_by(UserORM.created_at.desc()).limit(limit).offset(offset)
        )
        return [to_user(row) for row in result.all()]


class WalletRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_balance(self, user_id: int) -> Money:
        minor = await self._session.scalar(
            select(UserORM.balance_minor).where(UserORM.id == user_id)
        )
        return Money(int(minor or 0))

    async def apply(
        self,
        user_id: int,
        *,
        type: WalletTxnType,
        amount: Money,
        order_id: int | None = None,
        note: str | None = None,
    ) -> WalletTransaction:
        # Lock the user row so concurrent debits cannot both pass a balance check.
        row = await self._session.scalar(
            select(UserORM).where(UserORM.id == user_id).with_for_update()
        )
        if row is None:
            raise InsufficientBalance
        new_balance = row.balance_minor + amount.minor
        if new_balance < 0:
            raise InsufficientBalance
        row.balance_minor = new_balance
        txn = WalletTransactionORM(
            user_id=user_id,
            type=type.value,
            amount_minor=amount.minor,
            balance_after_minor=new_balance,
            order_id=order_id,
            note=note,
        )
        self._session.add(txn)
        await self._session.flush()
        return to_wallet_txn(txn)

    async def list_transactions(
        self, user_id: int, *, limit: int, offset: int
    ) -> tuple[list[WalletTransaction], int]:
        total = int(
            await self._session.scalar(
                select(func.count(WalletTransactionORM.id)).where(
                    WalletTransactionORM.user_id == user_id
                )
            )
            or 0
        )
        result = await self._session.scalars(
            select(WalletTransactionORM)
            .where(WalletTransactionORM.user_id == user_id)
            .order_by(WalletTransactionORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [to_wallet_txn(row) for row in result.all()], total
