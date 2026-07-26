"""Wallet read use-cases (balance & ledger).

Mutations to the balance happen only inside other transactional use-cases
(checkout, payment top-up) via `WalletRepository.apply`.
"""

from __future__ import annotations

from playnext.application.dto import PER_PAGE, Page
from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.core.money import Money
from playnext.domain.models import WalletTransaction


class WalletService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def balance(self, user_id: int) -> Money:
        async with self._uow() as uow:
            return await uow.wallet.get_balance(user_id)

    async def transactions(self, user_id: int, *, page: int = 1) -> Page[WalletTransaction]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.wallet.list_transactions(
                user_id, limit=PER_PAGE, offset=offset
            )
        return Page(items=tuple(items), total=total, page=page)
