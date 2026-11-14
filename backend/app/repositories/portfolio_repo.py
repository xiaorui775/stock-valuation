"""投资组合与持仓的数据访问（FR-PORT-01 / 02）。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models.portfolio import Portfolio, PortfolioHolding


class PortfolioRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    # ---- 组合 ----
    def list(self, user_id: int) -> list[Portfolio]:
        return list(
            self.db.scalars(
                select(Portfolio)
                .where(Portfolio.user_id == user_id)
                .order_by(Portfolio.sort_order, Portfolio.id)
            )
        )

    def get(self, user_id: int, portfolio_id: int) -> Optional[Portfolio]:
        return self.db.scalar(
            select(Portfolio).where(
                Portfolio.id == portfolio_id, Portfolio.user_id == user_id
            )
        )

    def get_by_name(self, user_id: int, name: str) -> Optional[Portfolio]:
        return self.db.scalar(
            select(Portfolio).where(
                Portfolio.user_id == user_id, Portfolio.name == name
            )
        )

    def add(self, portfolio: Portfolio) -> Portfolio:
        self.db.add(portfolio)
        self.db.flush()
        return portfolio

    def delete(self, portfolio: Portfolio) -> None:
        self.db.delete(portfolio)
        self.db.flush()

    def next_order(self, user_id: int) -> int:
        current = self.db.scalar(
            select(func.max(Portfolio.sort_order)).where(Portfolio.user_id == user_id)
        )
        return 0 if current is None else current + 1

    # ---- 持仓 ----
    def list_holdings(self, portfolio_id: int) -> list[PortfolioHolding]:
        return list(
            self.db.scalars(
                select(PortfolioHolding)
                .where(PortfolioHolding.portfolio_id == portfolio_id)
                .order_by(PortfolioHolding.id)
            )
        )

    def get_holding(self, portfolio_id: int, holding_id: int) -> Optional[PortfolioHolding]:
        return self.db.scalar(
            select(PortfolioHolding).where(
                PortfolioHolding.id == holding_id,
                PortfolioHolding.portfolio_id == portfolio_id,
            )
        )

    def get_holding_by_ticker(
        self, portfolio_id: int, ticker: str
    ) -> Optional[PortfolioHolding]:
        return self.db.scalar(
            select(PortfolioHolding).where(
                PortfolioHolding.portfolio_id == portfolio_id,
                PortfolioHolding.ticker == ticker,
            )
        )

    def add_holding(self, holding: PortfolioHolding) -> PortfolioHolding:
        self.db.add(holding)
        self.db.flush()
        return holding

    def delete_holding(self, holding: PortfolioHolding) -> None:
        self.db.delete(holding)
        self.db.flush()
