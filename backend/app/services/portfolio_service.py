"""投资组合服务：组合与持仓的增删改（FR-PORT-01 / 02）。

组合汇总（市值、盈亏、权重、汇率）在 M2-10 的 PortfolioSummaryService 中实现，
这里只负责录入，不臆造任何行情或换算结果。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.models.portfolio import Portfolio, PortfolioHolding
from app.repositories.portfolio_repo import PortfolioRepository
from app.services.market_service import MarketService

DEFAULT_PORTFOLIO = "我的组合"
SUPPORTED_CURRENCIES = {"CNY", "USD", "HKD"}


class PortfolioService:
    def __init__(self, db: OrmSession, market: MarketService | None = None) -> None:
        self.db = db
        self.repo = PortfolioRepository(db)
        self.market = market or MarketService()

    # ---- 组合 ----
    def list(self, user_id: int) -> list[dict[str, Any]]:
        """列出全部组合；首次访问自动创建一个默认组合（与自选股一致）。"""
        portfolios = self.repo.list(user_id)
        if not portfolios:
            portfolios = [self._create_default(user_id)]
        return [self._serialize(p) for p in portfolios]

    def create(
        self, user_id: int, name: str, base_currency: str = "CNY", note: str = ""
    ) -> dict[str, Any]:
        cleaned = self._clean_name(name)
        if self.repo.get_by_name(user_id, cleaned) is not None:
            raise AppError(ErrorCode.CONFLICT, f"组合「{cleaned}」已存在", 409)
        portfolio = self.repo.add(
            Portfolio(
                user_id=user_id,
                name=cleaned,
                base_currency=self._clean_currency(base_currency),
                note=(note or "").strip(),
                sort_order=self.repo.next_order(user_id),
            )
        )
        self.db.commit()
        self.db.refresh(portfolio)
        return self._serialize(portfolio)

    def update(
        self,
        user_id: int,
        portfolio_id: int,
        *,
        name: str | None = None,
        base_currency: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        portfolio = self._owned(user_id, portfolio_id)
        if name is not None:
            cleaned = self._clean_name(name)
            if cleaned != portfolio.name:
                if self.repo.get_by_name(user_id, cleaned) is not None:
                    raise AppError(ErrorCode.CONFLICT, f"组合「{cleaned}」已存在", 409)
                portfolio.name = cleaned
        if base_currency is not None:
            portfolio.base_currency = self._clean_currency(base_currency)
        if note is not None:
            portfolio.note = note.strip()
        self.db.commit()
        self.db.refresh(portfolio)
        return self._serialize(portfolio)

    def delete(self, user_id: int, portfolio_id: int) -> dict[str, Any]:
        portfolio = self._owned(user_id, portfolio_id)
        self.repo.delete(portfolio)
        self.db.commit()
        return {"id": portfolio_id, "deleted": True}

    def get(self, user_id: int, portfolio_id: int) -> dict[str, Any]:
        return self._serialize(self._owned(user_id, portfolio_id))

    # ---- 持仓 ----
    def list_holdings(self, user_id: int, portfolio_id: int) -> list[dict[str, Any]]:
        portfolio = self._owned(user_id, portfolio_id)
        return [self._serialize_holding(h) for h in self.repo.list_holdings(portfolio.id)]

    def add_holding(
        self,
        user_id: int,
        portfolio_id: int,
        *,
        ticker: str,
        quantity: float,
        avg_cost: float,
        currency: str | None = None,
        opened_on: date | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        portfolio = self._owned(user_id, portfolio_id)
        symbol = normalize_ticker(ticker)
        if not symbol:
            raise AppError(ErrorCode.UNPROCESSABLE, "请填写股票代码", 422)
        if self.repo.get_holding_by_ticker(portfolio.id, symbol) is not None:
            raise AppError(
                ErrorCode.CONFLICT, f"{symbol} 已在「{portfolio.name}」中", 409
            )
        self._check_numbers(quantity, avg_cost)
        # 无效代码由 provider 抛 TickerNotFound（404），不会写入占位数据
        quote, _meta = self.market.get_quote(symbol)
        holding = self.repo.add_holding(
            PortfolioHolding(
                portfolio_id=portfolio.id,
                ticker=quote.ticker,
                name=quote.name,
                market=quote.market.value,
                currency=self._clean_currency(currency or quote.currency or "CNY"),
                quantity=quantity,
                avg_cost=avg_cost,
                opened_on=opened_on,
                note=(note or "").strip(),
            )
        )
        self.db.commit()
        self.db.refresh(holding)
        return self._serialize_holding(holding)

    def update_holding(
        self,
        user_id: int,
        portfolio_id: int,
        holding_id: int,
        *,
        quantity: float | None = None,
        avg_cost: float | None = None,
        currency: str | None = None,
        opened_on: date | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        portfolio = self._owned(user_id, portfolio_id)
        holding = self._owned_holding(portfolio.id, holding_id)
        if quantity is not None or avg_cost is not None:
            self._check_numbers(
                quantity if quantity is not None else holding.quantity,
                avg_cost if avg_cost is not None else holding.avg_cost,
            )
        if quantity is not None:
            holding.quantity = quantity
        if avg_cost is not None:
            holding.avg_cost = avg_cost
        if currency is not None:
            holding.currency = self._clean_currency(currency)
        if opened_on is not None:
            holding.opened_on = opened_on
        if note is not None:
            holding.note = note.strip()
        self.db.commit()
        self.db.refresh(holding)
        return self._serialize_holding(holding)

    def delete_holding(
        self, user_id: int, portfolio_id: int, holding_id: int
    ) -> dict[str, Any]:
        portfolio = self._owned(user_id, portfolio_id)
        holding = self._owned_holding(portfolio.id, holding_id)
        self.repo.delete_holding(holding)
        self.db.commit()
        return {"id": holding_id, "deleted": True}

    # ------------------------------------------------------------------
    def _create_default(self, user_id: int) -> Portfolio:
        portfolio = self.repo.add(
            Portfolio(
                user_id=user_id,
                name=DEFAULT_PORTFOLIO,
                base_currency="CNY",
                sort_order=0,
            )
        )
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def _owned(self, user_id: int, portfolio_id: int) -> Portfolio:
        portfolio = self.repo.get(user_id, portfolio_id)
        if portfolio is None:
            raise AppError(ErrorCode.NOT_FOUND, "组合不存在", 404)
        return portfolio

    def _owned_holding(self, portfolio_id: int, holding_id: int) -> PortfolioHolding:
        holding = self.repo.get_holding(portfolio_id, holding_id)
        if holding is None:
            raise AppError(ErrorCode.NOT_FOUND, "持仓不存在", 404)
        return holding

    def _serialize(self, portfolio: Portfolio) -> dict[str, Any]:
        holdings = self.repo.list_holdings(portfolio.id)
        return {
            "id": portfolio.id,
            "name": portfolio.name,
            "base_currency": portfolio.base_currency,
            "note": portfolio.note,
            "sort_order": portfolio.sort_order,
            "holding_count": len(holdings),
            "holdings": [self._serialize_holding(h) for h in holdings],
            "created_at": portfolio.created_at,
            "updated_at": portfolio.updated_at,
        }

    @staticmethod
    def _serialize_holding(holding: PortfolioHolding) -> dict[str, Any]:
        return {
            "id": holding.id,
            "ticker": holding.ticker,
            "name": holding.name,
            "market": holding.market,
            "currency": holding.currency,
            "quantity": holding.quantity,
            "avg_cost": holding.avg_cost,
            "opened_on": holding.opened_on,
            "note": holding.note,
            "created_at": holding.created_at,
            "updated_at": holding.updated_at,
        }

    @staticmethod
    def _clean_name(name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise AppError(ErrorCode.UNPROCESSABLE, "组合名称不能为空", 422)
        return cleaned

    @staticmethod
    def _clean_currency(currency: str) -> str:
        cleaned = (currency or "").strip().upper()
        if cleaned not in SUPPORTED_CURRENCIES:
            raise AppError(
                ErrorCode.UNPROCESSABLE,
                f"不支持的币种 {cleaned or '（空）'}，可选 {'/'.join(sorted(SUPPORTED_CURRENCIES))}",
                422,
            )
        return cleaned

    @staticmethod
    def _check_numbers(quantity: float, avg_cost: float) -> None:
        if quantity < 0:
            raise AppError(ErrorCode.UNPROCESSABLE, "持仓数量不能为负", 422)
        if avg_cost < 0:
            raise AppError(ErrorCode.UNPROCESSABLE, "平均成本不能为负", 422)
