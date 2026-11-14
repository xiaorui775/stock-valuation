"""名称查询不得被当成代码（回归：搜索「英伟达」返回 ticker=英伟达，点开后误报限流）。"""
from __future__ import annotations

import pytest

from app.providers.akshare_global_provider import AkshareGlobalProvider
from app.providers.base import TickerNotFound
from app.providers.yfinance_provider import YFinanceProvider


class _NoSearch:
    """让 yfinance 的 Search 返回空，走「精确匹配兜底」分支。"""

    class Search:
        def __init__(self, *args, **kwargs):
            self.quotes = []


def test_yfinance_fallback_skips_cjk_query(monkeypatch):
    provider = YFinanceProvider()
    fake = type("FakeYF", (), {"Search": _NoSearch.Search})
    monkeypatch.setattr(provider, "_module", lambda: fake)
    assert provider.search("英伟达") == []


def test_yfinance_fallback_keeps_ascii_code(monkeypatch):
    provider = YFinanceProvider()
    fake = type("FakeYF", (), {"Search": _NoSearch.Search})
    monkeypatch.setattr(provider, "_module", lambda: fake)
    items = provider.search("AAPL")
    assert [i.ticker for i in items] == ["AAPL"]


@pytest.mark.parametrize("method", ["get_quote", "get_history", "get_financials", "get_news"])
def test_akshare_global_rejects_cjk_ticker(method):
    provider = AkshareGlobalProvider()
    with pytest.raises(TickerNotFound):
        getattr(provider, method)("英伟达")


@pytest.mark.parametrize("method", ["get_quote", "get_history", "get_financials", "get_news"])
def test_yfinance_rejects_cjk_ticker(method):
    provider = YFinanceProvider()
    with pytest.raises(TickerNotFound):
        getattr(provider, method)("英伟达")


# ----------------------------------------------------------------------
# 搜索路由：中文财经源优先，yfinance 仅作备选
# ----------------------------------------------------------------------
class _FakeProvider:
    def __init__(self, name, markets, results=None, fail=False):
        self.name = name
        self.markets = markets
        self.results = results or []
        self.fail = fail
        self.calls = 0

    def search(self, query):
        self.calls += 1
        if self.fail:
            raise RuntimeError("upstream down")
        return list(self.results)


def _instrument(ticker, name, provider):
    from app.providers.models import Instrument, Market

    return Instrument(ticker=ticker, name=name, market=Market.US, provider=provider)


def test_search_prefers_primary_and_skips_fallback():
    from app.providers.registry import ProviderRegistry

    primary = _FakeProvider("akshare-global", {"US", "HK"}, [_instrument("NVDA", "英伟达", "akshare-global")])
    fallback = _FakeProvider("yfinance", {"US", "HK"}, [_instrument("NVDA", "NVIDIA", "yfinance")])
    reg = ProviderRegistry()
    reg.register(fallback, ["US"])
    reg.register(primary, ["US"])
    reg.add_fallback("US", "yfinance")

    items = reg.search("英伟达")
    assert [i.provider for i in items] == ["akshare-global"]
    assert fallback.calls == 0


def test_search_uses_fallback_when_primary_empty():
    from app.providers.registry import ProviderRegistry

    primary = _FakeProvider("akshare-global", {"US", "HK"})
    fallback = _FakeProvider("yfinance", {"US", "HK"}, [_instrument("NVDA", "NVIDIA", "yfinance")])
    reg = ProviderRegistry()
    reg.register(fallback, ["US", "HK"])
    reg.register(primary, ["US", "HK"])
    reg.add_fallback("US", "yfinance")

    items = reg.search("NVIDIA")
    assert [i.provider for i in items] == ["yfinance"]


def test_search_uses_fallback_when_primary_fails():
    from app.providers.registry import ProviderRegistry

    primary = _FakeProvider("akshare-global", {"US", "HK"}, fail=True)
    fallback = _FakeProvider("yfinance", {"US", "HK"}, [_instrument("NVDA", "NVIDIA", "yfinance")])
    reg = ProviderRegistry()
    reg.register(fallback, ["US", "HK"])
    reg.register(primary, ["US", "HK"])
    reg.add_fallback("US", "yfinance")

    assert [i.provider for i in reg.search("NVIDIA")] == ["yfinance"]
