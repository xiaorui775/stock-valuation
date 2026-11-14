"""自选股分组与条目模型（FR-WATCH-01 / 02）。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WatchlistGroup(Base, TimestampMixin):
    __tablename__ = "watchlist_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    items: Mapped[list[WatchlistItem]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="WatchlistItem.sort_order",
    )

    __table_args__ = (
        Index("ix_watchlist_groups_user_name", "user_id", "name", unique=True),
        Index("ix_watchlist_groups_user_order", "user_id", "sort_order"),
    )


class WatchlistItem(Base, TimestampMixin):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("watchlist_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    market: Mapped[str] = mapped_column(String(10), nullable=False, default="UNKNOWN")
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    group: Mapped[WatchlistGroup] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_watchlist_items_group_ticker", "group_id", "ticker", unique=True),
        Index("ix_watchlist_items_group_order", "group_id", "sort_order"),
    )
