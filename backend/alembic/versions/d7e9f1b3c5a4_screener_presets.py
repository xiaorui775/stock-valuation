"""screener: index constituents and saved presets

Revision ID: d7e9f1b3c5a4
Revises: c3d5e7f9a1b2
Create Date: 2026-11-13 19:30:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d7e9f1b3c5a4"
down_revision = "c3d5e7f9a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "index_constituents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("index_key", sa.String(length=20), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
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
    )
    op.create_table(
        "screener_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
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
    with op.batch_alter_table("index_constituents", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_index_constituents_index_key"),
            ["index_key"],
            unique=False,
        )
        batch_op.create_index(
            "ix_index_constituents_key_ticker", ["index_key", "ticker"], unique=True
        )
        batch_op.create_index(
            "ix_index_constituents_key_order", ["index_key", "sort_order"], unique=False
        )
    with op.batch_alter_table("screener_presets", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_screener_presets_user_id"), ["user_id"], unique=False
        )
        batch_op.create_index(
            "ix_screener_presets_user_name", ["user_id", "name"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("screener_presets", schema=None) as batch_op:
        batch_op.drop_index("ix_screener_presets_user_name")
        batch_op.drop_index(batch_op.f("ix_screener_presets_user_id"))
    with op.batch_alter_table("index_constituents", schema=None) as batch_op:
        batch_op.drop_index("ix_index_constituents_key_order")
        batch_op.drop_index("ix_index_constituents_key_ticker")
        batch_op.drop_index(batch_op.f("ix_index_constituents_index_key"))
    op.drop_table("screener_presets")
    op.drop_table("index_constituents")
