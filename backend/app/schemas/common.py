"""统一响应包与元数据模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Meta(BaseModel):
    """数据血缘：来源、时间、缓存状态、缺失字段。"""

    source: str | None = Field(default=None, description="数据提供方，如 yfinance / akshare")
    as_of: datetime | None = Field(default=None, description="数据对应的时间点")
    cached: bool = Field(default=False, description="是否来自缓存")
    stale: bool = Field(default=False, description="缓存已过期，降级返回")
    missing_fields: list[str] = Field(default_factory=list, description="缺失字段列表")
    currency: str | None = Field(default=None, description="金额字段的币种")


class ListData[T](BaseModel):
    items: list[T]
    page: int = 1
    page_size: int = 50
    total: int = 0


class ApiResponse[T](BaseModel):
    data: T
    meta: Meta = Field(default_factory=Meta)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
