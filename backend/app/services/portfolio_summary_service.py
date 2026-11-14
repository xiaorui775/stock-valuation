"""组合汇总服务：取行情与汇率后交给纯计算模块（FR-PORT-03 / 04 / 07）。

并发受限（8 线程）；单条持仓取数失败只影响该行，不中断整个组合。
汇率只取真实值，取不到就按币种分组，不做估算（FR-PORT-04）。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.analysis.portfolio import HoldingRow, summarize
from app.core.errors import AppError
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService
from app.services.valuation_service import ValuationService

QUOTE_WORKERS = 8


class PortfolioSummaryService:
    def __init__(self, db: OrmSession, market: MarketService | None = None) -> None:
        self.db = db
        self.market = market or MarketService()
        self.portfolios = PortfolioService(db, self.market)

    def summary(self, user_id: int, portfolio_id: int) -> dict[str, Any]:
        portfolio = self.portfolios.get(user_id, portfolio_id)
        base_currency = portfolio["base_currency"]
        holdings = portfolio["holdings"]

        fx_rates, fx_rate_map = self._fx_rates(base_currency, holdings)
        rows: list[HoldingRow] = []
        if holdings:
            with ThreadPoolExecutor(max_workers=QUOTE_WORKERS) as pool:
                rows = list(
                    pool.map(lambda h: self._row(h, base_currency, fx_rate_map), holdings)
                )

        result = summarize(rows, base_currency)
        as_of = max(
            (row.as_of for row in rows if row.as_of is not None),
            default=None,
        )
        return {
            "portfolio_id": portfolio["id"],
            "name": portfolio["name"],
            "base_currency": base_currency,
            "as_of": as_of,
            "fx_rates": fx_rates,
            **result,
        }

    # ------------------------------------------------------------------
    def _fx_rates(
        self, base_currency: str, holdings: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, float | None]]:
        currencies = sorted(
            {h["currency"] for h in holdings if h.get("currency") and h["currency"] != base_currency}
        )
        rows: list[dict[str, Any]] = [
            {
                "currency": base_currency,
                "rate": 1.0,
                "source": "identity",
                "as_of": None,
                "symbol": None,
            }
        ]
        rate_map: dict[str, float | None] = {base_currency: 1.0}
        for currency in currencies:
            rate, meta = self.market.get_fx_rate(currency, base_currency)
            rate_map[currency] = rate
            rows.append(
                {
                    "currency": currency,
                    "rate": rate,
                    "source": meta.get("source"),
                    "as_of": meta.get("as_of"),
                    "symbol": meta.get("symbol"),
                }
            )
        return rows, rate_map

    def _row(
        self,
        holding: dict[str, Any],
        base_currency: str,
        rate_map: dict[str, float | None],
    ) -> HoldingRow:
        ticker = holding["ticker"]
        currency = holding.get("currency")
        name = holding["name"]
        market = holding["market"]
        price: float | None = None
        previous_close: float | None = None
        upside: float | None = None
        as_of: datetime | None = None
        error: str | None = None

        quote = None
        try:
            quote, _meta = self.market.get_quote(ticker)
            price = quote.price
            previous_close = quote.previous_close
            as_of = quote.as_of
            name = quote.name or name
            market = quote.market.value
            currency = currency or quote.currency
        except AppError as exc:
            error = exc.message

        if quote is not None:
            try:
                financials, _fmeta = self.market.get_financials(ticker)
                valuation = ValuationService(quote, financials).build()
                upside = (valuation.get("dcf") or {}).get("upside_pct")
            except AppError:
                pass

        fx_rate = 1.0 if currency == base_currency else rate_map.get(currency or "")
        return HoldingRow(
            ticker=ticker,
            name=name,
            market=market,
            currency=currency,
            quantity=holding["quantity"],
            avg_cost=holding["avg_cost"],
            price=price,
            previous_close=previous_close,
            fx_rate=fx_rate,
            dcf_upside_pct=upside,
            as_of=as_of,
            error=error,
        )
