"""常用对比组合的请求/响应模型（FR-RESEARCH-06）。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ComparePresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    tickers: list[str] = Field(min_length=2, max_length=6)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("组合名称不能为空")
        return cleaned

    @field_validator("tickers")
    @classmethod
    def _tickers_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("对比代码不能为空")
        return value


class ComparePresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    tickers: list[str] | None = Field(default=None, min_length=2, max_length=6)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("组合名称不能为空")
        return cleaned


class ComparePresetOut(BaseModel):
    id: int
    name: str
    tickers: list[str]
    created_at: datetime
    updated_at: datetime


class ComparePresetListOut(BaseModel):
    items: list[ComparePresetOut]
