"""筛选器接口的请求与响应模型（§5.11 FR-SCR-01 ~ 06）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MetricKey = Literal[
    "market_cap",
    "pe_ttm",
    "forward_pe",
    "peg",
    "price_to_book",
    "price_to_sales",
    "ev_ebitda",
    "dividend_yield",
    "revenue_growth",
    "fcf_yield",
    "dcf_upside_pct",
    "beta",
]

MarketKey = Literal["US", "HK", "CN"]


class FilterRuleIn(BaseModel):
    metric: MetricKey
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def _needs_a_bound(self) -> FilterRuleIn:
        if self.min is None and self.max is None:
            raise ValueError("筛选条件至少要有一个边界（min 或 max）")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("下限不能大于上限")
        return self


class ScreenerPoolIn(BaseModel):
    kind: Literal["custom", "watchlist", "index"] = "custom"
    tickers: list[str] = Field(default_factory=list, max_length=500)
    watchlist_id: int | None = None
    index_key: str | None = None


class ScreenerRequest(BaseModel):
    pool: ScreenerPoolIn
    market: list[MarketKey] | None = None
    filters: list[FilterRuleIn] = Field(default_factory=list, max_length=12)
    sort_key: MetricKey | None = None
    sort_desc: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class ScreenerRowOut(BaseModel):
    ticker: str
    name: str
    market: str
    currency: str | None = None
    price: float | None = None
    market_cap: float | None = None
    pe_ttm: float | None = None
    forward_pe: float | None = None
    peg: float | None = None
    price_to_book: float | None = None
    price_to_sales: float | None = None
    ev_ebitda: float | None = None
    dividend_yield: float | None = None
    revenue_growth: float | None = None
    fcf_yield: float | None = None
    dcf_upside_pct: float | None = None
    beta: float | None = None
    as_of: datetime | None = None


class ScreenerFailureOut(BaseModel):
    ticker: str
    reason: str


class ScreenerOut(BaseModel):
    as_of: datetime
    page: int
    page_size: int
    total: int
    requested: int
    succeeded: int
    failed: int
    failures: list[ScreenerFailureOut]
    rows: list[ScreenerRowOut]
    elapsed_ms: int
    estimate_seconds: float
    note: str


# ----------------------------------------------------------------------
# 预设指数与筛选预设（M2-13）
# ----------------------------------------------------------------------


class IndexMemberOut(BaseModel):
    ticker: str
    name: str = ""


class IndexSummaryOut(BaseModel):
    key: str
    label: str
    count: int
    source: str
    updated_at: datetime | None = None


class IndexDetailOut(IndexSummaryOut):
    members: list[IndexMemberOut]


class IndexRefreshOut(BaseModel):
    key: str
    label: str
    refreshed: bool
    reason: str | None = None
    count: int
    source: str
    updated_at: datetime | None = None


class ScreenerPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    payload: ScreenerRequest


class ScreenerPresetOut(BaseModel):
    id: int
    name: str
    payload: ScreenerRequest
    created_at: datetime
    updated_at: datetime


class ScreenerPresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    payload: ScreenerRequest | None = None
