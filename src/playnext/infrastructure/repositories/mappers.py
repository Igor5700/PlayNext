"""Translate ORM rows <-> domain entities. Keeps repositories declarative."""

from __future__ import annotations

from playnext.core.money import Money
from playnext.domain.enums import DiscountType, OrderStatus, WalletTxnType
from playnext.domain.models import (
    Category,
    Order,
    OrderItem,
    Product,
    PromoCode,
    User,
    WalletTransaction,
)
from playnext.infrastructure.db.models import (
    CategoryORM,
    OrderItemORM,
    OrderORM,
    ProductORM,
    PromoCodeORM,
    UserORM,
    WalletTransactionORM,
)


def to_user(row: UserORM) -> User:
    return User(
        id=row.id,
        username=row.username,
        first_name=row.first_name,
        balance=Money(row.balance_minor),
        is_blocked=row.is_blocked,
        created_at=row.created_at,
    )


def to_category(row: CategoryORM, *, product_count: int = 0) -> Category:
    return Category(
        id=row.id,
        title=row.title,
        sort_order=row.sort_order,
        is_active=row.is_active,
        product_count=product_count,
    )


def to_product(row: ProductORM, *, stock: int = 0) -> Product:
    return Product(
        id=row.id,
        category_id=row.category_id,
        title=row.title,
        description=row.description,
        price=Money(row.price_minor),
        stock=stock,
        image_file_id=row.image_file_id,
        is_active=row.is_active,
        is_featured=row.is_featured,
        variant_group=row.variant_group,
        created_at=row.created_at,
    )


def to_order_item(row: OrderItemORM, *, keys: tuple[str, ...] = ()) -> OrderItem:
    return OrderItem(
        product_id=row.product_id or 0,
        title=row.title,
        unit_price=Money(row.unit_price_minor),
        quantity=row.quantity,
        delivered_keys=keys,
    )


def to_order(row: OrderORM, items: tuple[OrderItem, ...]) -> Order:
    return Order(
        id=row.id,
        user_id=row.user_id,
        status=OrderStatus(row.status),
        subtotal=Money(row.subtotal_minor),
        discount=Money(row.discount_minor),
        total=Money(row.total_minor),
        items=items,
        promo_code=row.promo_code,
        created_at=row.created_at,
    )


def to_wallet_txn(row: WalletTransactionORM) -> WalletTransaction:
    return WalletTransaction(
        id=row.id,
        user_id=row.user_id,
        type=WalletTxnType(row.type),
        amount=Money(row.amount_minor),
        balance_after=Money(row.balance_after_minor),
        order_id=row.order_id,
        note=row.note,
        created_at=row.created_at,
    )


def to_promo(row: PromoCodeORM) -> PromoCode:
    return PromoCode(
        code=row.code,
        discount_type=DiscountType(row.discount_type),
        value=row.value,
        is_active=row.is_active,
        max_uses=row.max_uses,
        used_count=row.used_count,
        min_subtotal=Money(row.min_subtotal_minor),
        valid_until=row.valid_until,
    )
