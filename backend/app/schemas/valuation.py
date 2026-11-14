"""估值接口的响应模型。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ValuationInputs(BaseModel):
    base_fcf: float | None = None
    base_fcf_year: int | None = None
    base_fcf_source: str | None = None
    """基准 FCF 的来源：最新年报 / 用户输入。"""
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


class SummaryMethod(BaseModel):
    """参与综合估值的方法及其权重（百分点）。"""

    name: str
    value: float
    weight: float


class Summary(BaseModel):
    average_value: float
    methods_used: int
    methods: list[SummaryMethod] = []
    vs_price_pct: float
    band: str
    note: str


class ValuationOut(BaseModel):
    ticker: str
    currency: str | None = None
    price: float | None = None
    inputs: ValuationInputs
    sources: dict[str, Any] = {}
    """假设来源：FCF 财年、资产负债表取数、总股本、Beta 与 CAPM 过程（FR-VAL-06）。"""
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


class MultiStageAssumptions(BaseModel):
    growth: float
    years1: int
    fade_years: int
    terminal: float
    discount: float
    discount_default_capm: float
    base_fcf: Optional[float] = None
    base_fcf_source: str
    ddm_growth: float


class MultiStageDcfOut(BaseModel):
    per_share: float
    upside_pct: Optional[float] = None
    enterprise_value: float
    equity_value: float
    base_fcf: Optional[float] = None
    pv_terminal_ratio: Optional[float] = None
    years: int


class MultiStageDdmOut(BaseModel):
    per_share: float
    upside_pct: Optional[float] = None
    dividend_yield: float
    dps: float
    pv_explicit: float
    pv_fade: float
    pv_terminal: float
    terminal_ratio: Optional[float] = None
    years: int


class MultiStageOut(BaseModel):
    """三阶段 DCF / DDM（FR-VAL-12）。DDM 仅对有股息的标的返回。"""

    ticker: str
    currency: Optional[str] = None
    price: Optional[float] = None
    assumptions: MultiStageAssumptions
    dcf: Optional[MultiStageDcfOut] = None
    ddm: Optional[MultiStageDdmOut] = None
    ddm_reason: Optional[str] = None
    missing: list[str] = []
    formula: str
    disclaimer: str


class WeightItem(BaseModel):
    name: str
    weight: float = Field(ge=0, le=100)


class SummaryWeightsRequest(BaseModel):
    methods: list[WeightItem] = Field(min_length=1, max_length=5)


class AvailableMethodOut(BaseModel):
    name: str
    value: float


class SummaryMethodOut(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float


class SummaryWeightsOut(BaseModel):
    """用户自定义权重的综合估值（FR-VAL-13）。"""

    available: list[AvailableMethodOut]
    weighted_value: Optional[float] = None
    vs_price_pct: Optional[float] = None
    band: Optional[str] = None
    methods: list[SummaryMethodOut] = []
    total_weight: float
    error: Optional[str] = None
