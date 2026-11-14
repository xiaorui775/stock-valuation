"""投资组合与持仓模型（FR-PORT-01 / 02）。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Portfolio(Base, TimestampMixin):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    holdings: Mapped[list[PortfolioHolding]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioHolding.id",
    )

    __table_args__ = (
        Index("ix_portfolios_user_name", "user_id", "name", unique=True),
        Index("ix_portfolios_user_order", "user_id", "sort_order"),
    )


class PortfolioHolding(Base, TimestampMixin):
    """一条持仓。

    `quantity` 与 `avg_cost` 用 Float 而不是 Numeric：这里只做展示与研究，不记账，
    小数精度差异不会累积成对账错误。允许数量为 0（已清仓但保留记录）。
    """

    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    market: Mapped[str] = mapped_column(String(10), nullable=False, default="UNKNOWN")
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    opened_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")

    __table_args__ = (
        Index("ix_portfolio_holdings_portfolio_ticker", "portfolio_id", "ticker", unique=True),
    )
