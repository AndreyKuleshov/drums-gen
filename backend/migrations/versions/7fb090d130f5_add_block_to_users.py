"""add block to users

Revision ID: 7fb090d130f5
Revises: 1dff0a81a3e9
Create Date: 2026-09-16 13:37:48.249461

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "7fb090d130f5"
down_revision: str | None = "1dff0a81a3e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "is_blocked")
