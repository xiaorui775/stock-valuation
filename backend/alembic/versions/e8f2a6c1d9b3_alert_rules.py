"""alert: 提醒规则表

Revision ID: e8f2a6c1d9b3
Revises: d7e9f1b3c5a4
Create Date: 2026-11-14 06:10:00
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e8f2a6c1d9b3"
down_revision = "d7e9f1b3c5a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("channels_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_value", sa.Float(), nullable=True),
        sa.Column("skip_reason", sa.String(length=200), nullable=True),
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
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])
    op.create_index("ix_alert_rules_ticker", "alert_rules", ["ticker"])
    op.create_index("ix_alert_rules_user_ticker", "alert_rules", ["user_id", "ticker"])


def downgrade() -> None:
    op.drop_index("ix_alert_rules_user_ticker", table_name="alert_rules")
    op.drop_index("ix_alert_rules_ticker", table_name="alert_rules")
    op.drop_index("ix_alert_rules_user_id", table_name="alert_rules")
    op.drop_table("alert_rules")
