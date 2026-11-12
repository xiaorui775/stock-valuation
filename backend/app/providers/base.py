"""Provider 抽象：统一数据源接口与异常。"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.providers.models import (
    Bar,
    CalendarInfo,
    Financials,
    Instrument,
    Market,
    NewsItem,
    Quote,
)


class ProviderError(Exception):
    """provider 内部错误的基类。"""


class ProviderUnavailable(ProviderError):
    """上游不可用（网络、限流、解析失败）。"""


class TickerNotFound(ProviderError):
    """代码无效或没有数据。"""


class RateLimited(ProviderError):
    """上游限流。"""


@runtime_checkable
class MarketDataProvider(Protocol):
    """数据源协议。实现者只需保证返回统一的模型。"""

    name: str
    markets: set[str]

    def search(self, query: str) -> list[Instrument]: ...

    def get_quote(self, ticker: str) -> Quote: ...

    def get_history(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> list[Bar]: ...

    def get_financials(self, ticker: str, period: str = "annual", limit: int = 5) -> Financials: ...

    def get_news(self, ticker: str) -> list[NewsItem]: ...

    def get_calendar(self, ticker: str) -> CalendarInfo | None: ...


def detect_market(ticker: str) -> Market:
    """按代码后缀判断市场：.SS/.SZ/.BJ → CN，.HK → HK，其余 → US。"""
    t = (ticker or "").strip().upper()
    if t.endswith((".SS", ".SZ", ".BJ")):
        return Market.CN
    if t.endswith(".HK"):
        return Market.HK
    return Market.US
