"""单只标的的行情 + 派生指标，供对比与筛选共用。

行情失败抛 `AppError`（由调用方决定是整列报错还是整行失败）；财务数据失败只让
派生指标为 None，行情字段照常返回——缺财报不等于没有行情。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import AppError
from app.services.financials_service import build_view
from app.services.market_service import MarketService
from app.services.valuation_service import ValuationService


def fetch_metrics(market: MarketService, ticker: str) -> dict[str, Any]:
    quote, _meta = market.get_quote(ticker)
    row: dict[str, Any] = {
        "ticker": quote.ticker,
        "name": quote.name,
        "market": quote.market.value,
        "currency": quote.currency,
        "price": quote.price,
        "previous_close": quote.previous_close,
        "market_cap": quote.market_cap,
        "pe_ttm": quote.pe_ttm,
        "forward_pe": quote.forward_pe,
        "peg": quote.peg,
        "price_to_book": quote.price_to_book,
        "price_to_sales": quote.price_to_sales,
        "ev_ebitda": quote.ev_ebitda,
        "dividend_yield": quote.dividend_yield,
        "beta": quote.beta,
        "revenue_growth": None,
        "gross_margin": None,
        "net_margin": None,
        "fcf_yield": None,
        "dcf_per_share": None,
        "dcf_upside_pct": None,
        "as_of": quote.as_of,
    }

    try:
        financials, _fmeta = market.get_financials(ticker)
    except AppError:
        return row

    if financials.years:
        view = build_view(financials)
        latest = view["years"][0]
        revenue = latest.get("revenue")
        row["revenue_growth"] = latest["yoy"]["revenue"]
        row["gross_margin"] = _ratio(latest.get("gross_profit"), revenue)
        row["net_margin"] = _ratio(latest.get("net_income"), revenue)

    try:
        valuation = ValuationService(quote, financials).build()
    except AppError:
        return row

    dcf = valuation.get("dcf") or {}
    row["dcf_per_share"] = dcf.get("per_share")
    row["dcf_upside_pct"] = dcf.get("upside_pct")
    row["fcf_yield"] = next(
        (
            item["value"]
            for item in valuation.get("multiples", [])
            if item["name"] == "FCF Yield"
        ),
        None,
    )
    return row


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100


def as_of_of(row: dict[str, Any]) -> datetime | None:
    value = row.get("as_of")
    return value if isinstance(value, datetime) else None
