"""Admin router tree.

The `IsAdmin` filter is applied to every admin subrouter's message and callback
observers — authorization is enforced structurally, so no admin handler can ever
be reached by a non-admin (unlike the old code, where it was absent entirely).
"""

from __future__ import annotations

from aiogram import Router

from playnext.presentation.filters.admin import IsAdmin
from playnext.presentation.routers.admin import (
    broadcast,
    categories,
    dashboard,
    orders,
    payments,
    products,
    promo,
    users,
)

admin_router = Router(name="admin")

_SUBROUTERS = (
    dashboard.router,
    categories.router,
    products.router,
    orders.router,
    payments.router,
    users.router,
    promo.router,
    broadcast.router,
)

for _router in _SUBROUTERS:
    _router.message.filter(IsAdmin())
    _router.callback_query.filter(IsAdmin())
    admin_router.include_router(_router)


__all__ = ["admin_router"]
