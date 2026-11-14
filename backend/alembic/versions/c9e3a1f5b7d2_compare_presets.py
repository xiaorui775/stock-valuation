"""compare_presets: 常用对比组合

Revision ID: c9e3a1f5b7d2
Revises: b7d1f4a8c2e6
Create Date: 2026-11-14 11:10:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c9e3a1f5b7d2"
down_revision = "b7d1f4a8c2e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compare_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("tickers_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_compare_presets_user_id", "compare_presets", ["user_id"])
    op.create_index(
        "ix_compare_presets_user_name", "compare_presets", ["user_id", "name"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_compare_presets_user_name", table_name="compare_presets")
    op.drop_index("ix_compare_presets_user_id", table_name="compare_presets")
    op.drop_table("compare_presets")
