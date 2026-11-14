"""历史估值区间的响应模型（FR-VAL-11）。"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PercentileStatsOut(BaseModel):
    p10: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p90: float | None = None
    count: int


class MetricHistoryOut(BaseModel):
    key: str
    label: str
    unit: str
    current: float | None = None
    percentile_3y: float | None = None
    percentile_5y: float | None = None
    stats_3y: PercentileStatsOut | None = None
    stats_5y: PercentileStatsOut | None = None
    note: str | None = None


class ValuationHistoryOut(BaseModel):
    ticker: str
    currency: str | None = None
    as_of: date
    windows: dict[str, date]
    sample_hint: str
    metrics: list[MetricHistoryOut]
    warnings: list[str]
