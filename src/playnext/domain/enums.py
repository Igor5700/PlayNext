"""Domain enumerations shared across layers."""

from __future__ import annotations

from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"  # created, awaiting fulfilment
    PAID = "paid"  # wallet debited
    FULFILLED = "fulfilled"  # keys delivered
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

    @property
    def is_terminal(self) -> bool:
        return self in (OrderStatus.FULFILLED, OrderStatus.CANCELLED, OrderStatus.REFUNDED)


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class WalletTxnType(StrEnum):
    TOPUP = "topup"  # money in (external payment)
    PURCHASE = "purchase"  # money out (order)
    REFUND = "refund"  # money in (order reversal)


class StockKeyStatus(StrEnum):
    AVAILABLE = "available"
    SOLD = "sold"


class DiscountType(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"
