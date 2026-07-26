"""Application services and the DI container that groups them."""

from __future__ import annotations

from dataclasses import dataclass

from playnext.application.ports.payment_gateway import PaymentGateway
from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.application.services.admin_service import AdminService
from playnext.application.services.cart_service import CartService
from playnext.application.services.catalog_service import CatalogService
from playnext.application.services.checkout_service import CheckoutService
from playnext.application.services.favorites_service import FavoritesService
from playnext.application.services.payment_service import PaymentService
from playnext.application.services.profile_service import ProfileService
from playnext.application.services.wallet_service import WalletService


@dataclass(frozen=True, slots=True)
class Services:
    """The set of use-case services injected into presentation handlers."""

    catalog: CatalogService
    cart: CartService
    checkout: CheckoutService
    wallet: WalletService
    payment: PaymentService
    profile: ProfileService
    favorites: FavoritesService
    admin: AdminService


def build_services(
    uow_factory: UnitOfWorkFactory,
    *,
    gateways: dict[str, PaymentGateway],
) -> Services:
    return Services(
        catalog=CatalogService(uow_factory),
        cart=CartService(uow_factory),
        checkout=CheckoutService(uow_factory),
        wallet=WalletService(uow_factory),
        payment=PaymentService(uow_factory, gateways=gateways),
        profile=ProfileService(uow_factory),
        favorites=FavoritesService(uow_factory),
        admin=AdminService(uow_factory),
    )


__all__ = [
    "AdminService",
    "CartService",
    "CatalogService",
    "CheckoutService",
    "FavoritesService",
    "PaymentService",
    "ProfileService",
    "Services",
    "WalletService",
    "build_services",
]
