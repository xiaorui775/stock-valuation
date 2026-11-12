"""估值接口的响应模型。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ValuationInputs(BaseModel):
    base_fcf: float | None = None
    base_fcf_year: int | None = None
    growth: float
    years1: int
    terminal: float
    discount: float
    discount_default_capm: float
    beta: float | None = None
    total_debt: float | None = None
    total_cash: float | None = None
    shares_outstanding: float | None = None
    balance_note: str | None = None
    ddm_growth: float


class DcfResult(BaseModel):
    per_share: float
    upside_pct: float | None = None
    enterprise_value: float
    equity_value: float
    base_fcf: float | None = None
    pv_terminal_ratio: float | None = None
    formula: str


class SensitivityRow(BaseModel):
    discount: float
    values: list[Optional[float]]


class Sensitivity(BaseModel):
    terminal_growths: list[float]
    rows: list[SensitivityRow]


class Multiple(BaseModel):
    name: str
    value: float | None = None
    formula: str


class DdmResult(BaseModel):
    per_share: float
    dividend_yield: float
    growth: float
    discount: float
    formula: str


class Summary(BaseModel):
    average_value: float
    methods_used: int
    vs_price_pct: float
    band: str
    note: str


class ValuationOut(BaseModel):
    ticker: str
    currency: str | None = None
    price: float | None = None
    inputs: ValuationInputs
    dcf: DcfResult | None = None
    sensitivity: Sensitivity | None = None
    multiples: list[Multiple]
    ddm: DdmResult | None = None
    graham: float | None = None
    summary: Summary | None = None
    disclaimer: str


class ScenarioItem(BaseModel):
    name: str
    growth: Optional[float] = None
    terminal: Optional[float] = None
    discount: Optional[float] = None
    probability: float = 0
    per_share: Optional[float] = None
    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    upside_pct: Optional[float] = None
    error: Optional[str] = None


class ScenarioRequest(BaseModel):
    scenarios: list[dict[str, Any]] = Field(min_length=1, max_length=5)


class ScenariosOut(BaseModel):
    scenarios: list[ScenarioItem]
    weighted: Optional[float] = None
    weighted_upside_pct: Optional[float] = None
    error: Optional[str] = None


class ReverseRequest(BaseModel):
    price: Optional[float] = None
    terminal: Optional[float] = None
    discount: Optional[float] = None
    years1: Optional[int] = Field(default=None, ge=1, le=20)


class ReverseOut(BaseModel):
    implied_growth: Optional[float] = None
    value_at_solution: Optional[float] = None
    range: Optional[list[float]] = None
    reason: Optional[str] = None


class WaccOut(BaseModel):
    inputs: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    formula: str
