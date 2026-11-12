"""行情、财务、新闻接口的响应模型。"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.providers.models import Market


class QuoteOut(BaseModel):
    ticker: str
    name: str
    currency: str | None = None
    market: Market = Market.UNKNOWN
    price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    open_price: float | None = None
    market_cap: float | None = None
    pe_ttm: float | None = None
    forward_pe: float | None = None
    eps_ttm: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    week52_high: float | None = None
    week52_low: float | None = None
    volume: float | None = None
    shares_outstanding: float | None = None
    price_to_book: float | None = None
    price_to_sales: float | None = None
    ev_ebitda: float | None = None
    peg: float | None = None
    total_debt: float | None = None
    total_cash: float | None = None
    total_revenue: float | None = None
    ebitda: float | None = None
    book_value_per_share: float | None = None
    as_of: datetime | None = None

    model_config = {"from_attributes": True}


class BarOut(BaseModel):
    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: float | None = None

    model_config = {"from_attributes": True}


class HistoryOut(BaseModel):
    ticker: str
    period: str
    interval: str
    bars: list[BarOut]


class FinancialYearOut(BaseModel):
    year: int
    period_end: date | None = None
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None
    free_cash_flow: float | None = None
    total_debt: float | None = None
    total_cash: float | None = None
    total_equity: float | None = None
    shares_outstanding: float | None = None

    model_config = {"from_attributes": True}


class FinancialsOut(BaseModel):
    ticker: str
    currency: str | None = None
    period: str
    years: list[FinancialYearOut]


class NewsItemOut(BaseModel):
    title: str
    url: str | None = None
    source: str | None = None
    kind: str
    published_at: datetime | None = None
    summary: str | None = None

    model_config = {"from_attributes": True}


class NewsListOut(BaseModel):
    ticker: str
    items: list[NewsItemOut]


class InstrumentOut(BaseModel):
    ticker: str
    name: str
    market: Market = Market.UNKNOWN
    exchange: str | None = None
    currency: str | None = None
    provider: str | None = None

    model_config = {"from_attributes": True}
