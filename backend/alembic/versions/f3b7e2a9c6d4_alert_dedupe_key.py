"""alert: 去重键（重启不重复通知）

Revision ID: f3b7e2a9c6d4
Revises: e8f2a6c1d9b3
Create Date: 2026-11-14 09:10:00

提醒功能已于 2026-11-14 取消（PRD v1.1 §5.13），本迁移仅保留历史，
保证已升级的数据库 alembic 版本链连续；不再有代码读写该列。
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f3b7e2a9c6d4"
down_revision = "e8f2a6c1d9b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alert_rules",
        sa.Column("dedupe_key", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table("alert_rules") as batch:
        batch.drop_column("dedupe_key")
