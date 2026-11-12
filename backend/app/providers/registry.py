"""Provider 注册表：按市场与代码路由主/备数据源，并处理降级。"""
from __future__ import annotations

from typing import Optional

from app.core.errors import AppError, ErrorCode
from app.providers.base import (
    MarketDataProvider,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    TickerNotFound,
    detect_market,
)
from app.providers.models import (
    Bar,
    CalendarInfo,
    Financials,
    Instrument,
    Market,
    NewsItem,
    Quote,
)
from app.providers.yfinance_provider import YFinanceProvider


class ProviderRegistry:
    """维护各市场的主备 provider。"""

    def __init__(self) -> None:
        self._providers: dict[str, MarketDataProvider] = {}
        self._routes: dict[str, list[str]] = {}

    def register(self, provider: MarketDataProvider, primary_markets: list[str]) -> None:
        self._providers[provider.name] = provider
        for market in primary_markets:
            self._routes.setdefault(market, []).insert(0, provider.name)

    def add_fallback(self, market: str, provider_name: str) -> None:
        """把 provider 追加到该市场的备选链末尾。"""
        chain = self._routes.setdefault(market, [])
        if provider_name not in chain:
            chain.append(provider_name)

    def get(self, name: str) -> MarketDataProvider:
        return self._providers[name]

    def chain_for(self, ticker: str) -> list[MarketDataProvider]:
        market = detect_market(ticker)
        names = self._routes.get(market.value, [])
        if not names:
            names = self._routes.get(Market.US.value, [])
        return [self._providers[n] for n in names if n in self._providers]

    # ------------------------------------------------------------------
    # 带降级的调用
    # ------------------------------------------------------------------
    def _try_chain(self, ticker: str, action: str):
        """依次尝试主备 provider，全部失败则抛出最合适的异常。"""
        chain = self.chain_for(ticker)
        if not chain:
            raise AppError(ErrorCode.DATA_UNAVAILABLE, "没有可用的数据源", 503)
        last_error: Exception | None = None
        for provider in chain:
            try:
                return getattr(provider, action)(ticker)
            except TickerNotFound:
                raise  # 代码无效时不必换源
            except (ProviderUnavailable, RateLimited, ProviderError) as exc:
                last_error = exc
                continue
            except Exception as exc:  # 上游字段变化等意外错误
                last_error = ProviderUnavailable(str(exc))
                continue
        if isinstance(last_error, RateLimited):
            raise AppError(ErrorCode.RATE_LIMITED, "数据源限流，请稍后重试", 429)
        raise AppError(
            ErrorCode.DATA_UNAVAILABLE,
            f"数据源暂时不可用：{last_error}" if last_error else "数据源暂时不可用",
            503,
        )

    def get_quote(self, ticker: str) -> Quote:
        return self._try_chain(ticker, "get_quote")

    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> list[Bar]:
        chain = self.chain_for(ticker)
        last_error: Exception | None = None
        for provider in chain:
            try:
                return provider.get_history(ticker, period=period, interval=interval)
            except TickerNotFound:
                raise
            except Exception as exc:
                last_error = exc
                continue
        raise AppError(
            ErrorCode.DATA_UNAVAILABLE,
            f"历史价格获取失败：{last_error}" if last_error else "历史价格获取失败",
            503,
        )

    def get_financials(self, ticker: str, period: str = "annual", limit: int = 5) -> Financials:
        return self._try_chain(ticker, "get_financials")

    def get_news(self, ticker: str) -> list[NewsItem]:
        chain = self.chain_for(ticker)
        last_error: Exception | None = None
        for provider in chain:
            try:
                return provider.get_news(ticker)
            except TickerNotFound:
                raise
            except Exception as exc:
                last_error = exc
                continue
        raise AppError(
            ErrorCode.DATA_UNAVAILABLE,
            f"新闻获取失败：{last_error}" if last_error else "新闻获取失败",
            503,
        )

    def get_calendar(self, ticker: str) -> Optional[CalendarInfo]:
        for provider in self.chain_for(ticker):
            try:
                info = provider.get_calendar(ticker)
            except Exception:
                continue
            if info is not None:
                return info
        return None

    def search(self, query: str, market: Optional[str] = None) -> list[Instrument]:
        results: list[Instrument] = []
        seen: set[str] = set()
        for provider in self._providers.values():
            if market and market not in provider.markets:
                continue
            try:
                items = provider.search(query)
            except Exception:
                continue
            for item in items:
                if item.ticker in seen:
                    continue
                seen.add(item.ticker)
                results.append(item)
        return results


registry = ProviderRegistry()
registry.register(YFinanceProvider(), [Market.US.value, Market.HK.value])
