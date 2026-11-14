"""财务解读服务：取数与规则执行（§5.6）。"""
from __future__ import annotations

from typing import Any

from app.analysis.financial_insights import analyze
from app.core.errors import AppError
from app.services.market_service import MarketService


class InsightService:
    def __init__(self, market: MarketService | None = None) -> None:
        self.market = market or MarketService()

    def get(self, ticker: str) -> tuple[dict[str, Any], dict[str, Any]]:
        quote, meta = self.market.get_quote(ticker)
        financials = None
        try:
            financials, _ = self.market.get_financials(ticker)
        except AppError:
            # 财报缺失时只有「数据不足」结论，不影响行情接口
            financials = None
        result = analyze(financials.years if financials else [], quote)
        data = {
            "ticker": quote.ticker,
            "currency": quote.currency,
            "fiscal_year": result["fiscal_year"],
            "items": result["items"],
            "uncovered": result["uncovered"],
            "summary": result["summary"],
        }
        return data, meta
