"""valuation presets

Revision ID: 7c1d9e4b2a30
Revises: 2cf6ebf215c1
Create Date: 2026-11-12 22:15:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "7c1d9e4b2a30"
down_revision = "2cf6ebf215c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "valuation_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("assumptions_json", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("valuation_presets", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_valuation_presets_ticker"), ["ticker"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_valuation_presets_user_id"), ["user_id"], unique=False
        )
        batch_op.create_index(
            "ix_valuation_presets_user_ticker_name",
            ["user_id", "ticker", "name"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("valuation_presets", schema=None) as batch_op:
        batch_op.drop_index("ix_valuation_presets_user_ticker_name")
        batch_op.drop_index(batch_op.f("ix_valuation_presets_user_id"))
        batch_op.drop_index(batch_op.f("ix_valuation_presets_ticker"))
    op.drop_table("valuation_presets")
