"""估值预设接口的请求与响应模型（FR-VAL-07）。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PresetAssumptions(BaseModel):
    """与估值接口的输入参数同名同口径（百分数为百分点）。"""

    base_fcf: float | None = None
    growth: float | None = Field(default=None, ge=-100, le=200)
    years1: int | None = Field(default=None, ge=1, le=20)
    terminal: float | None = Field(default=None, ge=-50, le=50)
    discount: float | None = Field(default=None, ge=0.1, le=100)
    ddm_growth: float | None = Field(default=None, ge=-50, le=50)


class PresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    assumptions: PresetAssumptions


class PresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    assumptions: PresetAssumptions | None = None


class PresetOut(BaseModel):
    id: int
    ticker: str
    name: str
    assumptions: PresetAssumptions
    created_at: datetime
    updated_at: datetime


class PresetListOut(BaseModel):
    items: list[PresetOut]


class PresetComparisonRow(BaseModel):
    """单个预设在同一份行情/财报下的估值结果与生效假设。"""

    preset_id: int
    name: str
    growth: float
    years1: int
    terminal: float
    discount: float
    ddm_growth: float
    base_fcf: float | None = None
    per_share: float | None = None
    upside_pct: float | None = None
    pv_terminal_ratio: float | None = None
    note: str | None = None


class PresetComparisonOut(BaseModel):
    ticker: str
    price: float | None = None
    currency: str | None = None
    items: list[PresetComparisonRow]
    notes: list[str] = Field(default_factory=list)


class DeletedOut(BaseModel):
    id: int
    deleted: bool = True
