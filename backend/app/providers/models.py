"""数据源统一模型：所有 provider 输出先转换为这些结构。"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Market(str, Enum):
    US = "US"
    HK = "HK"
    CN = "CN"
    UNKNOWN = "UNKNOWN"


class Instrument(BaseModel):
    """标的元信息。"""

    ticker: str
    name: str
    market: Market = Market.UNKNOWN
    exchange: str | None = None
    currency: str | None = None
    provider: str | None = None
    source_meta: dict[str, Any] = Field(default_factory=dict)


class Quote(BaseModel):
    """行情快照。所有数值字段缺失时为 None，不得填充 0。"""

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
    dividend_yield: float | None = Field(default=None, description="百分数，10 表示 10%")
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
    provider: str | None = None
    missing_fields: list[str] = Field(default_factory=list)


class Bar(BaseModel):
    """单根 K 线 / 日线数据点。"""

    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: float | None = None
    adj_close: float | None = None


class FinancialYear(BaseModel):
    """单个财年的财务数据。"""

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


class Financials(BaseModel):
    """财务数据集。"""

    ticker: str
    currency: str | None = None
    period: str = "annual"
    years: list[FinancialYear] = Field(default_factory=list)
    provider: str | None = None
    missing_fields: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    """新闻或公告条目。"""

    title: str
    url: str | None = None
    source: str | None = None
    kind: str = "news"  # news | announcement
    published_at: datetime | None = None
    publisher: str | None = None
    summary: str | None = None


class CalendarInfo(BaseModel):
    """财报日历等事件信息。"""

    earnings_date: date | None = None
    dividend_date: date | None = None
    ex_dividend_date: date | None = None
