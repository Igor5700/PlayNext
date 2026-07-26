"""financial invariant check constraints

Defense in depth alongside the existing application-level checks (e.g.
WalletRepository.apply already refuses to let a balance go negative) — these
make the same invariants true even for a write that bypasses the app layer.

Uses batch mode so this also runs against the SQLite fallback used for local
dev/tests (SQLite can't ALTER a table to add a constraint directly; batch mode
recreates the table under the hood). Batch mode is a no-op wrapper on
Postgres — it still emits a plain ALTER TABLE ADD CONSTRAINT there.

Revision ID: 0004_financial_check_constraints
Revises: 0003_product_variant_group
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_financial_check_constraints"
down_revision: str | None = "0003_product_variant_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_check_constraint(
            "ck_users_balance_minor_non_negative", "balance_minor >= 0"
        )
    with op.batch_alter_table("products") as batch_op:
        batch_op.create_check_constraint("ck_products_price_minor_positive", "price_minor > 0")
    with op.batch_alter_table("cart_items") as batch_op:
        batch_op.create_check_constraint("ck_cart_items_quantity_positive", "quantity > 0")
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.create_check_constraint("ck_order_items_quantity_positive", "quantity > 0")
    with op.batch_alter_table("payments") as batch_op:
        batch_op.create_check_constraint("ck_payments_amount_minor_positive", "amount_minor > 0")


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint("ck_payments_amount_minor_positive", type_="check")
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_constraint("ck_order_items_quantity_positive", type_="check")
    with op.batch_alter_table("cart_items") as batch_op:
        batch_op.drop_constraint("ck_cart_items_quantity_positive", type_="check")
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint("ck_products_price_minor_positive", type_="check")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_balance_minor_non_negative", type_="check")
