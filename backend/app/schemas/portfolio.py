"""投资组合接口的请求与响应模型（FR-PORT-01 / 02）。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Currency = Literal["CNY", "USD", "HKD"]


class HoldingOut(BaseModel):
    id: int
    ticker: str
    name: str
    market: str
    currency: str | None = None
    quantity: float
    avg_cost: float
    opened_on: date | None = None
    note: str = ""
    created_at: datetime
    updated_at: datetime


class PortfolioOut(BaseModel):
    id: int
    name: str
    base_currency: str
    note: str = ""
    sort_order: int
    holding_count: int
    holdings: list[HoldingOut]
    created_at: datetime
    updated_at: datetime


class PortfolioListOut(BaseModel):
    items: list[PortfolioOut]


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    base_currency: Currency = "CNY"
    note: str = Field(default="", max_length=500)


class PortfolioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    base_currency: Currency | None = None
    note: str | None = Field(default=None, max_length=500)


class HoldingCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    quantity: float = Field(ge=0)
    avg_cost: float = Field(ge=0)
    currency: Currency | None = Field(
        default=None, description="不填则取行情的计价货币"
    )
    opened_on: date | None = None
    note: str = Field(default="", max_length=500)


class HoldingUpdate(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    avg_cost: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    opened_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


# ----------------------------------------------------------------------
# 组合汇总（FR-PORT-03 / 04 / 07）
# ----------------------------------------------------------------------


class FxRateOut(BaseModel):
    """一条汇率：1 单位 currency 折合多少基础货币。"""

    currency: str
    rate: float | None = None
    source: str | None = None
    as_of: datetime | None = None
    symbol: str | None = None


class HoldingSummaryOut(BaseModel):
    ticker: str
    name: str
    market: str
    currency: str | None = None
    quantity: float
    avg_cost: float
    price: float | None = None
    previous_close: float | None = None
    fx_rate: float | None = None
    dcf_upside_pct: float | None = None
    as_of: datetime | None = None
    error: str | None = None
    market_value_local: float | None = None
    market_value: float | None = None
    cost: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None
    day_pnl: float | None = None
    weight_pct: float | None = None
    converted: bool = False


class UnconvertedOut(BaseModel):
    """缺汇率的币种分组：只给本币小计，不换算。"""

    currency: str
    count: int
    priced_count: int = 0
    market_value_local: float | None = None


class MarketDistributionOut(BaseModel):
    market: str
    market_value: float | None = None
    weight_pct: float | None = None


class ConcentrationOut(BaseModel):
    ticker: str
    name: str
    weight_pct: float | None = None


class PortfolioSummaryOut(BaseModel):
    portfolio_id: int
    name: str
    base_currency: str
    as_of: datetime | None = None
    total_market_value: float | None = None
    total_cost: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None
    day_pnl: float | None = None
    day_pnl_pct: float | None = None
    weighted_upside_pct: float | None = None
    upside_coverage_pct: float | None = None
    rows: list[HoldingSummaryOut]
    fx_rates: list[FxRateOut]
    unconverted: list[UnconvertedOut]
    distribution: list[MarketDistributionOut]
    concentration: list[ConcentrationOut]
    warnings: list[str]
