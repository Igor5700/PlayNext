"""Concurrency tests that require real Postgres row-locking.

SQLite (used by the rest of the suite, see conftest.py) silently no-ops
`FOR UPDATE` / `FOR UPDATE SKIP LOCKED` — SQLAlchemy's SQLite dialect compiles
both to an empty string (`SQLiteCompiler.for_update_clause` returns `""`), so
it cannot exercise the row-level locking that `WalletRepository.apply` and
`StockKeyRepository.consume` rely on for correctness. These tests run only
against a real Postgres, given via `TEST_DATABASE_URL` (a
`postgresql+asyncpg://` DSN pointing at a throwaway/test database) — they are
skipped otherwise, e.g. on a machine without Docker. CI provides Postgres as a
service container (see .github/workflows/ci.yml) with this variable set.
"""

from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker

from playnext.application.ports.payment_gateway import GatewayPayment
from playnext.application.services import Services, build_services
from playnext.core.money import Money
from playnext.domain.enums import PaymentStatus, WalletTxnType
from playnext.domain.errors import InsufficientBalance, OutOfStock
from playnext.domain.models import Product
from playnext.infrastructure.db import models  # noqa: F401 - register tables
from playnext.infrastructure.db.base import Base
from playnext.infrastructure.db.engine import build_engine
from playnext.infrastructure.db.unit_of_work import make_uow_factory

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "set TEST_DATABASE_URL (postgresql+asyncpg://...) to run the row-locking "
        "tests against real Postgres — skipped on SQLite-only machines"
    ),
)


class _FakeGateway:
    """Auto-approving gateway double — unused by these tests but required to
    construct Services; no network calls."""

    name = "fake"

    async def create_payment(
        self, *, amount: Money, description: str, idempotence_key: str
    ) -> GatewayPayment:
        return GatewayPayment(provider_payment_id="fake", status=PaymentStatus.PENDING)

    async def get_payment(self, provider_payment_id: str) -> GatewayPayment:
        return GatewayPayment(
            provider_payment_id=provider_payment_id, status=PaymentStatus.SUCCEEDED
        )


@pytest_asyncio.fixture
async def pg_uow_factory():
    engine = build_engine(TEST_DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except OperationalError as exc:  # pragma: no cover - environment guard
        await engine.dispose()
        pytest.skip(f"cannot reach TEST_DATABASE_URL: {exc}")
        return
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    yield make_uow_factory(session_factory)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def pg_services(pg_uow_factory) -> Services:
    return build_services(pg_uow_factory, gateways={"fake": _FakeGateway()})


async def _fund_user(uow_factory, user_id: int, balance_major: int) -> None:
    async with uow_factory() as uow:
        await uow.users.get_or_create(user_id, username="user", first_name="User")
        await uow.wallet.apply(
            user_id, type=WalletTxnType.TOPUP, amount=Money.from_major(balance_major)
        )
        await uow.commit()


async def _make_product(services: Services, *, price: int, stock: int) -> Product:
    category = await services.admin.create_category(title="Steam")
    product = await services.admin.create_product(
        category_id=category.id,
        title="GTA V",
        description="demo",
        price=Money.from_major(price),
        image_file_id=None,
    )
    await services.admin.add_keys(product.id, [f"KEY-{i}" for i in range(stock)])
    return product


async def test_concurrent_checkout_never_double_sells_last_key(pg_services, pg_uow_factory) -> None:
    """Two buyers race for the single remaining key via genuinely concurrent transactions.

    This is the guarantee `test_no_double_sell_of_last_key` in test_checkout.py cannot
    exercise on SQLite: `FOR UPDATE SKIP LOCKED` on stock_keys must let exactly one of
    two truly-concurrent `place_order` calls win.
    """
    await _fund_user(pg_uow_factory, 9100, 5000)
    await _fund_user(pg_uow_factory, 9101, 5000)
    product = await _make_product(pg_services, price=1000, stock=1)
    await pg_services.cart.add(9100, product.id, quantity=1)
    await pg_services.cart.add(9101, product.id, quantity=1)

    results = await asyncio.gather(
        pg_services.checkout.place_order(9100),
        pg_services.checkout.place_order(9101),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, BaseException)]
    failures = [r for r in results if isinstance(r, BaseException)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], OutOfStock)
    assert await pg_services.admin.keys_available(product.id) == 0


async def test_concurrent_wallet_debits_never_go_negative(pg_services, pg_uow_factory) -> None:
    """Two purchases racing against a balance that can only cover one must not both succeed.

    Exercises `SELECT ... FOR UPDATE` on the user row in WalletRepository.apply.
    """
    await _fund_user(pg_uow_factory, 9200, 1000)
    product = await _make_product(pg_services, price=1000, stock=5)
    await pg_services.cart.add(9200, product.id, quantity=1)

    async def _buy_once() -> object:
        return await pg_services.checkout.place_order(9200)

    results = await asyncio.gather(_buy_once(), _buy_once(), return_exceptions=True)

    successes = [r for r in results if not isinstance(r, BaseException)]
    failures = [r for r in results if isinstance(r, BaseException)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], InsufficientBalance)
    balance = await pg_services.wallet.balance(9200)
    assert balance.minor == 0
    assert await pg_services.admin.keys_available(product.id) == 4
