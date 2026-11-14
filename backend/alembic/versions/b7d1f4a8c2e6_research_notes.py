"""research_notes: 研究笔记（结论/假设/待验证问题）

Revision ID: b7d1f4a8c2e6
Revises: f3b7e2a9c6d4
Create Date: 2026-11-14 10:20:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b7d1f4a8c2e6"
down_revision = "f3b7e2a9c6d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("preset_id", sa.Integer(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["preset_id"], ["valuation_presets.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_research_notes_user_id", "research_notes", ["user_id"])
    op.create_index("ix_research_notes_ticker", "research_notes", ["ticker"])
    op.create_index(
        "ix_research_notes_user_ticker", "research_notes", ["user_id", "ticker"]
    )


def downgrade() -> None:
    op.drop_index("ix_research_notes_user_ticker", table_name="research_notes")
    op.drop_index("ix_research_notes_ticker", table_name="research_notes")
    op.drop_index("ix_research_notes_user_id", table_name="research_notes")
    op.drop_table("research_notes")
