"""Test fixtures: an isolated in-memory database and a wired service container."""

from __future__ import annotations

from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from playnext.application.ports.payment_gateway import GatewayPayment
from playnext.application.services import Services, build_services
from playnext.core.money import Money
from playnext.domain.enums import PaymentStatus
from playnext.infrastructure.db import models  # noqa: F401 - register tables
from playnext.infrastructure.db.base import Base
from playnext.infrastructure.db.unit_of_work import make_uow_factory


class FakeGateway:
    """Auto-approving gateway double — no network calls, for tests only."""

    name = "fake"

    async def create_payment(
        self, *, amount: Money, description: str, idempotence_key: str
    ) -> GatewayPayment:
        return GatewayPayment(
            provider_payment_id=f"fake-{uuid4().hex[:16]}", status=PaymentStatus.PENDING
        )

    async def get_payment(self, provider_payment_id: str) -> GatewayPayment:
        return GatewayPayment(
            provider_payment_id=provider_payment_id, status=PaymentStatus.SUCCEEDED
        )


@pytest_asyncio.fixture
async def uow_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    yield make_uow_factory(session_factory)
    await engine.dispose()


@pytest_asyncio.fixture
async def services(uow_factory) -> Services:
    return build_services(uow_factory, gateways={"fake": FakeGateway()})
