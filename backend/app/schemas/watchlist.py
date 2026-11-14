"""自选股接口的请求与响应模型（FR-WATCH-01 / 02）。"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class WatchlistItemOut(BaseModel):
    id: int
    ticker: str
    name: str
    market: str
    currency: str | None = None
    sort_order: int


class WatchlistGroupOut(BaseModel):
    id: int
    name: str
    sort_order: int
    items: list[WatchlistItemOut]


class WatchlistListOut(BaseModel):
    groups: list[WatchlistGroupOut]


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class GroupUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class GroupOrderUpdate(BaseModel):
    group_ids: list[int] = Field(min_length=1)


class ItemCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)


class BatchItemCreate(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=50)


class ItemOrderUpdate(BaseModel):
    item_ids: list[int] = Field(min_length=1)


class FailedItem(BaseModel):
    ticker: str
    reason: str


class BatchResultOut(BaseModel):
    added: list[WatchlistItemOut]
    failed: list[FailedItem]


class WatchlistQuoteOut(BaseModel):
    """自选股行情的单元格（FR-WATCH-03）。"""

    ticker: str
    name: str | None = None
    market: str = "UNKNOWN"
    currency: str | None = None
    price: float | None = None
    change_pct: float | None = None
    market_cap: float | None = None
    pe_ttm: float | None = None
    forward_pe: float | None = None
    dividend_yield: float | None = None
    fcf_yield: float | None = None
    dcf_upside_pct: float | None = None
    # 下一次财报日（FR-RESEARCH-04）：仅展示，不做提醒
    earnings_date: date | None = None
    days_until_earnings: int | None = None
    earnings_source: str | None = None
    as_of: datetime | None = None
    stale: bool = False
    error: str | None = None


class WatchlistQuotesOut(BaseModel):
    group_id: int
    items: list[WatchlistQuoteOut]
    refreshed_at: datetime
