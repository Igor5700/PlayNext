"""add products.variant_group

Revision ID: 0003_product_variant_group
Revises: 0002_product_is_featured
Create Date: 2026-07-07
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_product_variant_group"
down_revision: str | None = "0002_product_is_featured"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("variant_group", sa.String(64), nullable=True))
    op.create_index("ix_products_variant_group", "products", ["variant_group"])


def downgrade() -> None:
    op.drop_index("ix_products_variant_group", table_name="products")
    op.drop_column("products", "variant_group")
