"""规则化财务解读的响应模型（§5.6）。"""
from __future__ import annotations

from pydantic import BaseModel


class InsightItemOut(BaseModel):
    rule: str
    name: str
    level: str
    title: str
    detail: str
    formula: str
    value: float | None = None
    period: str | None = None


class UncoveredRuleOut(BaseModel):
    rule: str
    name: str
    reason: str


class InsightsOut(BaseModel):
    ticker: str
    currency: str | None = None
    fiscal_year: int | None = None
    items: list[InsightItemOut]
    uncovered: list[UncoveredRuleOut]
    summary: str
