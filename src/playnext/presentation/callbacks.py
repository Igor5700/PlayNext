"""Typed callback data — the entire navigation graph in one place.

Every inline button carries a structured, validated payload instead of an ad-hoc
`"prefix:1:2"` string. Parsing is done by aiogram's CallbackData factory, so a
malformed or stale callback is rejected before it reaches a handler.
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class Nav(CallbackData, prefix="nav"):
    """Top-level navigation between the main sections."""

    to: str  # home | catalog | favorites | cart | profile | orders | wallet | search | support


class CatalogCB(CallbackData, prefix="cat"):
    category_id: int
    page: int = 1


class CatalogFilterCB(CallbackData, prefix="catf"):
    """Quick-filter shelves on the catalog home screen.

    Field is named `kind`, not `filter` — CallbackData already defines a
    `.filter(...)` classmethod (used everywhere as `SomeCB.filter(F.x == y)`),
    so a same-named field would shadow it.
    """

    kind: str  # newest | popular | discounts | recent
    page: int = 1


class ProductCB(CallbackData, prefix="prod"):
    action: str  # open | add | buy_now | favorite | share
    product_id: int
    category_id: int = 0
    page: int = 1


class GroupCB(CallbackData, prefix="grp"):
    """A product variant group (e.g. GTA 6 editions) shown as one catalog entry."""

    group: str


class FeaturedCB(CallbackData, prefix="ftr"):
    """The featured-games showcase on the catalog home screen — cycle by index."""

    index: int = 0


class FavoriteCB(CallbackData, prefix="fav"):
    """The standalone favorites list — paginate only.

    Adding/removing always happens from the product card (ProductCB action
    "favorite"); tapping an item here opens its card too, for one consistent
    "tap a product row -> see its card" rule everywhere in the catalog.
    """

    action: str  # list
    page: int = 1


class CartCB(CallbackData, prefix="crt"):
    action: str  # inc | dec | del | clear | checkout
    product_id: int = 0


class CheckoutCB(CallbackData, prefix="co"):
    action: str  # confirm | promo | clearpromo | back


class WalletCB(CallbackData, prefix="wal"):
    action: str  # topup | preset | provider | history
    amount: int = 0  # preset amount, major units
    page: int = 1
    provider: str = ""  # used with action="provider": demo | crypto_pay


class PayCB(CallbackData, prefix="pay"):
    action: str  # check | cancel
    payment_id: int


class OrdersCB(CallbackData, prefix="ord"):
    action: str  # list | open
    order_id: int = 0
    page: int = 1


class SearchCB(CallbackData, prefix="srch"):
    page: int = 1


# ── Admin ────────────────────────────────────────────────────────────────────
class AdminCB(CallbackData, prefix="adm"):
    to: str  # home | cats | prods | orders | users | promos | broadcast


class AdminCatCB(CallbackData, prefix="admcat"):
    action: str  # open | add | rename | toggle | del
    category_id: int = 0


class AdminProdCB(CallbackData, prefix="admprd"):
    action: str  # list | open | add | title | price | desc | image | keys | toggle | del
    product_id: int = 0
    page: int = 1


class AdminOrderCB(CallbackData, prefix="admord"):
    action: str  # list | open
    order_id: int = 0
    page: int = 1


class AdminUserCB(CallbackData, prefix="admusr"):
    action: str  # list | block | unblock
    user_id: int = 0
    page: int = 1


class AdminPromoCB(CallbackData, prefix="admpr"):
    action: str  # list | add | toggle
    code: str = ""


class AdminPayCB(CallbackData, prefix="admpay"):
    action: str  # list
    page: int = 1


class Noop(CallbackData, prefix="noop"):
    """A button that only acknowledges (e.g. the page indicator)."""

    tag: str = "x"
