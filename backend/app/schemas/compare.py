"""多股对比接口的响应模型（§5.10 FR-CMP-01 ~ 04）。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CompareTickerOut(BaseModel):
    ticker: str
    name: str
    market: str
    currency: str | None = None
    error: str | None = None


class ComparePointOut(BaseModel):
    date: str
    value: float


class CompareMetricOut(BaseModel):
    key: str
    label: str
    unit: str
    direction: str | None = None
    values: dict[str, float | None]
    best: str | None = None
    worst: str | None = None
    missing: list[str] = Field(default_factory=list)
    """缺失该指标的标的，供前端标注「—（数据缺失）」且不参与优/差评选。"""


class UnifiedAssumptionsOut(BaseModel):
    growth: float
    years1: int
    terminal: float
    note: str


class CompareValuationRowOut(BaseModel):
    ticker: str
    price: float | None = None
    per_share: float | None = None
    upside_pct: float | None = None


class CompareValuationOut(BaseModel):
    assumptions: UnifiedAssumptionsOut
    rows: list[CompareValuationRowOut]


class CompareOut(BaseModel):
    as_of: datetime
    period: str
    tickers: list[CompareTickerOut]
    series: dict[str, list[ComparePointOut]]
    metrics: list[CompareMetricOut]
    valuation: CompareValuationOut
    warnings: list[str]
