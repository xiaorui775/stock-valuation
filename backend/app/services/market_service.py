"""行情服务：编排缓存与 provider，负责降级与数据血缘组装。"""
from __future__ import annotations

from typing import Any, Optional

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.providers.cache import TtlCache, cache_key, l1_cache
from app.providers.demo_provider import DemoProvider
from app.providers.models import (
    Bar,
    Financials,
    Instrument,
    NewsItem,
    Quote,
)
from app.providers.registry import ProviderRegistry, registry

logger = get_logger("market")


class MarketService:
    def __init__(self, cache: TtlCache | None = None, providers: ProviderRegistry | None = None) -> None:
        self.settings = get_settings()
        self.cache = cache if cache is not None else l1_cache
        self.registry = providers if providers is not None else registry
        self._demo = DemoProvider()
        self.demo_mode = self.settings.demo

    # ------------------------------------------------------------------
    def _ttl(self, kind: str) -> int:
        s = self.settings
        return {
            "quote": s.cache_ttl_quote_seconds,
            "history": s.cache_ttl_history_seconds,
            "financials": s.cache_ttl_financials_hours * 3600,
            "news": s.cache_ttl_news_minutes * 60,
            "metadata": s.cache_ttl_metadata_hours * 3600,
        }.get(kind, 60)

    # ------------------------------------------------------------------
    def get_quote(self, ticker: str) -> tuple[Quote, dict[str, Any]]:
        ticker = ticker.strip().upper()
        if self.demo_mode:
            quote = self._demo.get_quote(ticker)
            return quote, self._meta(quote.provider, quote.as_of, cached=False, stale=False,
                                     missing=quote.missing_fields, currency=quote.currency)

        key = cache_key("quote", ticker)
        entry = self.cache.get(key)
        if entry is not None and not entry.is_expired:
            quote = entry.value
            return quote, self._meta(quote.provider, quote.as_of, cached=True, stale=False,
                                     missing=quote.missing_fields, currency=quote.currency)

        try:
            quote = self.registry.get_quote(ticker)
        except AppError as exc:
            # 降级：返回过期的缓存数据
            if entry is not None:
                logger.warning("quote_stale_fallback", ticker=ticker, error=exc.message)
                quote = entry.value
                return quote, self._meta(quote.provider, quote.as_of, cached=True, stale=True,
                                         missing=quote.missing_fields, currency=quote.currency)
            raise

        self.cache.set(key, quote, self._ttl("quote"))
        return quote, self._meta(quote.provider, quote.as_of, cached=False, stale=False,
                                 missing=quote.missing_fields, currency=quote.currency)

    # ------------------------------------------------------------------
    def get_history(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> tuple[list[Bar], dict[str, Any]]:
        ticker = ticker.strip().upper()
        if self.demo_mode:
            bars = self._demo.get_history(ticker, period=period, interval=interval)
            return bars, self._meta(self._demo.name, None, cached=False, stale=False)

        key = cache_key("history", ticker, period, interval)
        entry = self.cache.get(key)
        if entry is not None and not entry.is_expired:
            return entry.value, self._meta("cache", None, cached=True, stale=False)

        try:
            bars = self.registry.get_history(ticker, period=period, interval=interval)
        except AppError as exc:
            if entry is not None:
                logger.warning("history_stale_fallback", ticker=ticker, error=exc.message)
                return entry.value, self._meta("cache", None, cached=True, stale=True)
            raise

        self.cache.set(key, bars, self._ttl("history"))
        return bars, self._meta("yfinance", None, cached=False, stale=False)

    # ------------------------------------------------------------------
    def get_financials(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> tuple[Financials, dict[str, Any]]:
        ticker = ticker.strip().upper()
        if self.demo_mode:
            financials = self._demo.get_financials(ticker, period=period, limit=limit)
            return financials, self._meta(self._demo.name, None, cached=False, stale=False)

        key = cache_key("financials", ticker, period, limit)
        entry = self.cache.get(key)
        if entry is not None and not entry.is_expired:
            return entry.value, self._meta(entry.value.provider, None, cached=True, stale=False)

        try:
            financials = self.registry.get_financials(ticker, period=period, limit=limit)
        except AppError as exc:
            if entry is not None:
                logger.warning("financials_stale_fallback", ticker=ticker, error=exc.message)
                return entry.value, self._meta(entry.value.provider, None, cached=True, stale=True)
            raise

        self.cache.set(key, financials, self._ttl("financials"))
        return financials, self._meta(financials.provider, None, cached=False, stale=False)

    # ------------------------------------------------------------------
    def get_news(self, ticker: str) -> tuple[list[NewsItem], dict[str, Any]]:
        ticker = ticker.strip().upper()
        if self.demo_mode:
            return self._demo.get_news(ticker), self._meta(self._demo.name, None, cached=False, stale=False)

        key = cache_key("news", ticker)
        entry = self.cache.get(key)
        if entry is not None and not entry.is_expired:
            return entry.value, self._meta("cache", None, cached=True, stale=False)

        try:
            items = self.registry.get_news(ticker)
        except AppError:
            if entry is not None:
                return entry.value, self._meta("cache", None, cached=True, stale=True)
            raise

        self.cache.set(key, items, self._ttl("news"))
        return items, self._meta("yfinance", None, cached=False, stale=False)

    # ------------------------------------------------------------------
    def search(self, query: str, market: Optional[str] = None) -> tuple[list[Instrument], dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return [], self._meta(None, None, cached=False, stale=False)
        if self.demo_mode:
            items = self._demo.search(query)
            return items, self._meta(self._demo.name, None, cached=False, stale=False)

        key = cache_key("search", query, market or "")
        entry = self.cache.get(key)
        if entry is not None and not entry.is_expired:
            return entry.value, self._meta("cache", None, cached=True, stale=False)

        items = self.registry.search(query, market)
        self.cache.set(key, items, self._ttl("metadata"))
        return items, self._meta("yfinance", None, cached=False, stale=False)

    # ------------------------------------------------------------------
    def _meta(
        self,
        source: Optional[str],
        as_of: Any,
        cached: bool,
        stale: bool,
        missing: Optional[list[str]] = None,
        currency: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "source": source,
            "as_of": as_of,
            "cached": cached,
            "stale": stale,
            "missing_fields": missing or [],
            "currency": currency,
        }
