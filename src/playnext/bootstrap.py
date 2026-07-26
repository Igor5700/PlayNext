"""Composition root.

The single place where concrete implementations are wired to abstractions:
settings -> engine -> repositories (via UoW) -> services -> bot. Everything above
this file depends only on interfaces, which is what keeps the layers decoupled.
"""

from __future__ import annotations

import logging

import sentry_sdk
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonDefault

from playnext.application.services import build_services
from playnext.core.config import Settings, get_settings
from playnext.core.logging import setup_logging
from playnext.infrastructure.db.engine import build_engine, build_session_factory
from playnext.infrastructure.db.unit_of_work import make_uow_factory
from playnext.infrastructure.payments.factory import build_gateways
from playnext.presentation.middlewares import setup_middlewares
from playnext.presentation.routers import setup_routers

logger = logging.getLogger("playnext")

async def _clear_menu(bot: Bot) -> None:
    # No slash-command menu — navigation is inline-only, /start stays reachable
    # as a plain command handler without being advertised in the UI.
    await bot.delete_my_commands()
    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())


async def run(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    setup_logging(level=settings.log_level, json_output=settings.log_json)

    if settings.sentry_dsn:
        # Error tracking only — no performance/APM tracing, not needed at this scale.
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment.value,
            traces_sample_rate=0.0,
        )

    engine = build_engine(settings.database_url, echo=False)
    session_factory = build_session_factory(engine)
    uow_factory = make_uow_factory(session_factory)
    gateways = build_gateways(settings)
    services = build_services(uow_factory, gateways=gateways)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["services"] = services
    dp["settings"] = settings

    setup_middlewares(dp, uow_factory=uow_factory)
    setup_routers(dp)

    logger.info(
        "PlayNext starting (env=%s, payments=%s)",
        settings.environment.value,
        ", ".join(gateways),
    )
    try:
        await _clear_menu(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        # aiogram's own polling loop installs SIGTERM/SIGINT handlers by default
        # (handle_signals=True) on platforms that support loop.add_signal_handler
        # (Linux/macOS — i.e. the actual Docker deployment target; a no-op on
        # Windows, where Ctrl+C still reaches us as KeyboardInterrupt). On signal,
        # start_polling() stops cleanly and returns, so this `finally` always runs.
        await dp.start_polling(bot)
    finally:
        for gateway in gateways.values():
            aclose = getattr(gateway, "aclose", None)
            if aclose is not None:
                await aclose()
        await bot.session.close()
        await engine.dispose()
        logger.info("PlayNext stopped")
