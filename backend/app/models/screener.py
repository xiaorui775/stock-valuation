"""预设指数成分与筛选预设模型（§5.11）。"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IndexConstituent(Base, TimestampMixin):
    """指数的成分股缓存。

    成分会随指数调整变化，所以每行都保留 `source` 与 `updated_at`；接口据此
    告诉用户这份名单是什么时候、从哪里来的。
    """

    __tablename__ = "index_constituents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    __table_args__ = (
        Index("ix_index_constituents_key_ticker", "index_key", "ticker", unique=True),
        Index("ix_index_constituents_key_order", "index_key", "sort_order"),
    )


class ScreenerPreset(Base, TimestampMixin):
    """保存的筛选条件与股票池（FR-SCR-04）。payload 是请求体的 JSON。"""

    __tablename__ = "screener_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_screener_presets_user_name", "user_id", "name", unique=True),
    )
