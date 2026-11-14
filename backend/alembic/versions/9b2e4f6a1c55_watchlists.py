"""watchlists: groups and items

Revision ID: 9b2e4f6a1c55
Revises: 7c1d9e4b2a30
Create Date: 2026-11-12 22:40:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "9b2e4f6a1c55"
down_revision = "7c1d9e4b2a30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
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
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["group_id"], ["watchlist_groups.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("watchlist_groups", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_watchlist_groups_user_id"), ["user_id"], unique=False
        )
        batch_op.create_index(
            "ix_watchlist_groups_user_name", ["user_id", "name"], unique=True
        )
        batch_op.create_index(
            "ix_watchlist_groups_user_order", ["user_id", "sort_order"], unique=False
        )
    with op.batch_alter_table("watchlist_items", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_watchlist_items_group_id"), ["group_id"], unique=False
        )
        batch_op.create_index(
            "ix_watchlist_items_group_ticker", ["group_id", "ticker"], unique=True
        )
        batch_op.create_index(
            "ix_watchlist_items_group_order", ["group_id", "sort_order"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("watchlist_items", schema=None) as batch_op:
        batch_op.drop_index("ix_watchlist_items_group_order")
        batch_op.drop_index("ix_watchlist_items_group_ticker")
        batch_op.drop_index(batch_op.f("ix_watchlist_items_group_id"))
    with op.batch_alter_table("watchlist_groups", schema=None) as batch_op:
        batch_op.drop_index("ix_watchlist_groups_user_order")
        batch_op.drop_index("ix_watchlist_groups_user_name")
        batch_op.drop_index(batch_op.f("ix_watchlist_groups_user_id"))
    op.drop_table("watchlist_items")
    op.drop_table("watchlist_groups")
