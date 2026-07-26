"""drop categories.emoji

Part of the UI rework: the interface no longer renders emoji anywhere, so the
per-category icon column has no reader left. Batch mode for SQLite parity with
the rest of this migration chain (see 0004).

Revision ID: 0005_drop_category_emoji
Revises: 0004_financial_check_constraints
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_drop_category_emoji"
down_revision: str | None = "0004_financial_check_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_column("emoji")


def downgrade() -> None:
    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(sa.Column("emoji", sa.String(8), server_default="•"))
