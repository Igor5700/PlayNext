"""Presentation middlewares: identity, throttling, centralised error handling."""

from __future__ import annotations

from aiogram import Dispatcher

from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.presentation.middlewares.error import ErrorMiddleware
from playnext.presentation.middlewares.throttling import ThrottlingMiddleware
from playnext.presentation.middlewares.user import UserMiddleware


def setup_middlewares(dp: Dispatcher, *, uow_factory: UnitOfWorkFactory) -> None:
    # Outer middlewares run before filters, outermost first.
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(ErrorMiddleware())
        observer.outer_middleware(ThrottlingMiddleware())
        observer.outer_middleware(UserMiddleware(uow_factory))


__all__ = ["ErrorMiddleware", "ThrottlingMiddleware", "UserMiddleware", "setup_middlewares"]
