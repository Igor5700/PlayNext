"""FSM state groups — small, feature-scoped, never one giant blob.

State is used only where genuine free-text input is required; all navigation is
stateless and callback-driven.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SearchFlow(StatesGroup):
    query = State()


class CheckoutFlow(StatesGroup):
    promo = State()


class WalletFlow(StatesGroup):
    amount = State()


class AdminCategoryFlow(StatesGroup):
    title = State()
    rename = State()


class AdminProductFlow(StatesGroup):
    category = State()
    title = State()
    description = State()
    price = State()
    image = State()
    edit_title = State()
    edit_price = State()
    edit_description = State()
    edit_image = State()
    keys = State()


class AdminPromoFlow(StatesGroup):
    code = State()
    discount = State()
    min_subtotal = State()


class AdminBroadcastFlow(StatesGroup):
    message = State()
