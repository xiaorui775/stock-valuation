"""搜索服务：代码识别、名称检索与结果排序。

对应 PRD §5.2：
- FR-SEARCH-02 代码格式识别（含 A 股纯数字代码的后缀提示）
- FR-SEARCH-03 名称搜索（优先数据源搜索接口，失败时退化为代码精确匹配）
- FR-SEARCH-05 无效代码不返回任何模拟数据
"""
from __future__ import annotations

from typing import Any, Optional

from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.core.tickers import (
    exchange_hint,
    is_code_like,
    market_label,
    normalize_ticker,
    parse_ticker,
)
from app.providers.cache import cache_key, l1_cache
from app.providers.demo_provider import DemoProvider
from app.providers.models import Instrument, InstrumentKind, Market
from app.providers.registry import ProviderRegistry, registry

logger = get_logger("search")


class SearchService:
    """编排搜索：缓存 → provider 链 → 本地精确匹配兜底。"""

    def __init__(
        self,
        providers: ProviderRegistry | None = None,
        cache: Any | None = None,
        demo_mode: Optional[bool] = None,
    ) -> None:
        self.registry = providers if providers is not None else registry
        self.cache = cache if cache is not None else l1_cache
        self._demo = DemoProvider()
        self.demo_mode = demo_mode

    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        market: Optional[str] = None,
        limit: int = 20,
    ) -> tuple[list[Instrument], dict[str, Any]]:
        """搜索标的，返回 (结果列表, meta)。"""
        raw = (query or "").strip()
        if not raw:
            return [], self._meta(None, cached=False)

        if self.demo_mode is None:
            from app.core.config import get_settings

            self.demo_mode = get_settings().demo
        if self.demo_mode:
            items = self._demo.search(raw)
            if market:
                items = [i for i in items if i.market.value == market]
            return items[:limit], self._meta(self._demo.name, cached=False)

        key = cache_key("search", raw, market or "")
        entry = self.cache.get(key)
        if entry is not None and not entry.is_expired:
            return list(entry.value)[:limit], self._meta("cache", cached=True)

        items = self._collect(raw, market)
        self.cache.set(key, items, self._ttl())
        source = items[0].provider if items else None
        return items[:limit], self._meta(source, cached=False)

    # ------------------------------------------------------------------
    def _collect(self, query: str, market: Optional[str]) -> list[Instrument]:
        """从 provider 链收集结果，并做去重与本地精确匹配补充。

        主源（中文财经站点）优先；主源无结果时才请求备选（yfinance）。
        """
        items = self._collect_from_groups(query, market)

        # 代码精确匹配兜底：provider 无结果时，至少给出规范化后的代码。
        if not items and is_code_like(query):
            items.append(self._exact_instrument(query))

        items = self._rank(items, query)
        return items

    def _collect_from_groups(self, query: str, market: Optional[str]) -> list[Instrument]:
        groups = self.registry.search_groups(market)
        for group in groups:
            items: list[Instrument] = []
            seen: set[str] = set()
            for provider in group:
                try:
                    found = provider.search(query)
                except Exception as exc:  # 上游字段变化等意外错误不应中断搜索
                    logger.warning(
                        "search_provider_failed", provider=provider.name, error=str(exc)
                    )
                    continue
                for item in found:
                    if item.ticker in seen:
                        continue
                    seen.add(item.ticker)
                    items.append(item)
            if items:
                return items
        return []

    # ------------------------------------------------------------------
    def _exact_instrument(self, query: str) -> Instrument:
        """按代码精确匹配构造的标的条目。"""
        info = parse_ticker(query)
        ticker = info.ticker
        note = "按代码精确匹配"
        if info.needs_suffix:
            note = f"按代码精确匹配，A 股代码通常需要补交易所后缀（{info.suffix_suggestion}）"
        return Instrument(
            ticker=ticker,
            name=ticker,
            market=info.market,
            exchange=exchange_hint(ticker),
            kind=InstrumentKind.EQUITY,
            provider="local",
            source_meta={"note": note, "suffix_suggestion": info.suffix_suggestion},
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _rank(items: list[Instrument], query: str) -> list[Instrument]:
        """排序：完全匹配 > 前缀匹配 > 名称包含 > 其余。"""
        q = normalize_ticker(query)
        lowered = (query or "").strip().lower()

        def score(item: Instrument) -> tuple[int, int]:
            ticker = item.ticker.upper()
            if ticker == q:
                return (0, 0)
            if ticker.startswith(q):
                return (1, 0)
            if item.name.lower() == lowered:
                return (1, 1)
            if lowered and lowered in item.name.lower():
                return (2, 0)
            if item.name.lower().startswith(lowered):
                return (3, 0)
            return (4, 0)

        return sorted(items, key=score)

    # ------------------------------------------------------------------
    @staticmethod
    def _ttl() -> int:
        from app.core.config import get_settings

        return get_settings().cache_ttl_metadata_hours * 3600

    @staticmethod
    def _meta(source: Optional[str], cached: bool) -> dict[str, Any]:
        return {
            "source": source,
            "as_of": None,
            "cached": cached,
            "stale": False,
            "missing_fields": [],
            "currency": None,
        }


# ----------------------------------------------------------------------
def resolve_ticker(raw: str) -> tuple[str, Market, Optional[str]]:
    """把用户输入的代码解析为 (代码, 市场, 后缀提示)。

    供个股页等场景直接使用：输入 `600519` 会得到提示 `.SS`。
    """
    info = parse_ticker(raw)
    return info.ticker, info.market, info.suffix_suggestion


def market_display(market: Market | str | None) -> str:
    """市场的中文标签，供接口返回。"""
    return market_label(market)


def require_ticker(raw: str) -> str:
    """校验并规范化代码；空输入抛 VALIDATION_ERROR。"""
    ticker = normalize_ticker(raw)
    if not ticker:
        raise AppError(ErrorCode.VALIDATION_ERROR, "股票代码不能为空", 422)
    return ticker
