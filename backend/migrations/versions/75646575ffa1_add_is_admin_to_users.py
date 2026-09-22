"""add is_admin to users

Revision ID: 75646575ffa1
Revises: 6c9c10b36b85
Create Date: 2026-09-15 17:40:02.592039

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "75646575ffa1"
down_revision: str | None = "6c9c10b36b85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
