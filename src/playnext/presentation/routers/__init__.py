"""Router registration. Order matters: specific feature routers first."""

from __future__ import annotations

from aiogram import Dispatcher

from playnext.presentation.routers import (
    cabinet,
    cart,
    catalog,
    fallback,
    favorites,
    start,
    wallet,
)
from playnext.presentation.routers.admin import admin_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(favorites.router)
    dp.include_router(cart.router)
    dp.include_router(wallet.router)
    dp.include_router(cabinet.router)
    dp.include_router(admin_router)
    dp.include_router(fallback.router)  # must be last
