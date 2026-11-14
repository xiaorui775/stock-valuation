"""portfolios: portfolios and holdings

Revision ID: c3d5e7f9a1b2
Revises: 9b2e4f6a1c55
Create Date: 2026-11-13 17:05:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c3d5e7f9a1b2"
down_revision = "9b2e4f6a1c55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
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
        "portfolio_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_cost", sa.Float(), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=False),
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
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_portfolios_user_id"), ["user_id"], unique=False
        )
        batch_op.create_index("ix_portfolios_user_name", ["user_id", "name"], unique=True)
        batch_op.create_index(
            "ix_portfolios_user_order", ["user_id", "sort_order"], unique=False
        )
    with op.batch_alter_table("portfolio_holdings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_portfolio_holdings_portfolio_id"),
            ["portfolio_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_portfolio_holdings_portfolio_ticker",
            ["portfolio_id", "ticker"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("portfolio_holdings", schema=None) as batch_op:
        batch_op.drop_index("ix_portfolio_holdings_portfolio_ticker")
        batch_op.drop_index(batch_op.f("ix_portfolio_holdings_portfolio_id"))
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        batch_op.drop_index("ix_portfolios_user_order")
        batch_op.drop_index("ix_portfolios_user_name")
        batch_op.drop_index(batch_op.f("ix_portfolios_user_id"))
    op.drop_table("portfolio_holdings")
    op.drop_table("portfolios")
