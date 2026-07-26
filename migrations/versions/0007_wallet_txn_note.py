"""add wallet_transactions.note

Revision ID: 0007_wallet_txn_note
Revises: 0006_favorites_recently_viewed
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_wallet_txn_note"
down_revision: str | None = "0006_favorites_recently_viewed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("wallet_transactions", sa.Column("note", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("wallet_transactions", "note")
