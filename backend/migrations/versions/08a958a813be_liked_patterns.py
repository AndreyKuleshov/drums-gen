"""liked patterns

Revision ID: 08a958a813be
Revises: 76812a11191f
Create Date: 2026-07-31 18:26:07.819845

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "08a958a813be"
down_revision: str | None = "76812a11191f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "liked_patterns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("phrase", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["drumgen.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="drumgen",
    )
    op.create_index(
        op.f("ix_drumgen_liked_patterns_created_at"),
        "liked_patterns",
        ["created_at"],
        unique=False,
        schema="drumgen",
    )
    op.create_index(
        op.f("ix_drumgen_liked_patterns_user_id"),
        "liked_patterns",
        ["user_id"],
        unique=False,
        schema="drumgen",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_drumgen_liked_patterns_user_id"), table_name="liked_patterns", schema="drumgen"
    )
    op.drop_index(
        op.f("ix_drumgen_liked_patterns_created_at"), table_name="liked_patterns", schema="drumgen"
    )
    op.drop_table("liked_patterns", schema="drumgen")
