"""pattern ratings

Revision ID: 1dff0a81a3e9
Revises: 75646575ffa1
Create Date: 2026-09-15 17:50:44.137076

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "1dff0a81a3e9"
down_revision: str | None = "75646575ffa1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pattern_ratings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rater_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column(
            "tags", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("pattern", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("generator_version", sa.String(length=32), nullable=False),
        sa.Column("moderated_out", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("moderated_by", sa.Uuid(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["rater_id"], ["drumgen.users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["moderated_by"], ["drumgen.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rater_id", "content_hash"),
        schema="drumgen",
    )
    op.create_index(
        op.f("ix_drumgen_pattern_ratings_rater_id"),
        "pattern_ratings",
        ["rater_id"],
        unique=False,
        schema="drumgen",
    )
    op.create_index(
        op.f("ix_drumgen_pattern_ratings_content_hash"),
        "pattern_ratings",
        ["content_hash"],
        unique=False,
        schema="drumgen",
    )
    op.create_index(
        op.f("ix_drumgen_pattern_ratings_created_at"),
        "pattern_ratings",
        ["created_at"],
        unique=False,
        schema="drumgen",
    )
    op.create_index(
        "ix_drumgen_pattern_ratings_tags",
        "pattern_ratings",
        ["tags"],
        unique=False,
        schema="drumgen",
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_drumgen_pattern_ratings_tags", table_name="pattern_ratings", schema="drumgen")
    op.drop_index(
        op.f("ix_drumgen_pattern_ratings_created_at"),
        table_name="pattern_ratings",
        schema="drumgen",
    )
    op.drop_index(
        op.f("ix_drumgen_pattern_ratings_content_hash"),
        table_name="pattern_ratings",
        schema="drumgen",
    )
    op.drop_index(
        op.f("ix_drumgen_pattern_ratings_rater_id"),
        table_name="pattern_ratings",
        schema="drumgen",
    )
    op.drop_table("pattern_ratings", schema="drumgen")
