"""add favorites and recently_viewed tables

Revision ID: 0006_favorites_recently_viewed
Revises: 0005_drop_category_emoji
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_favorites_recently_viewed"
down_revision: str | None = "0005_drop_category_emoji"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("product_id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "recently_viewed",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("product_id", sa.Integer(), primary_key=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("recently_viewed")
    op.drop_table("favorites")
