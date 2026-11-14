"""搜索接口测试。"""
from __future__ import annotations

from typing import ClassVar

from app.providers.models import Instrument, InstrumentKind, Market


def test_search_requires_auth(client):
    resp = client.get("/api/v1/search?q=AAPL")
    assert resp.status_code == 401


def test_search_returns_instrument(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=AAPL")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 1
    assert items[0]["ticker"] == "AAPL"


def test_search_requires_query(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=")
    assert resp.status_code == 422


def test_search_normalizes_case_and_spaces(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=%20aapl%20")
    assert resp.status_code == 200
    assert resp.json()["data"][0]["ticker"] == "AAPL"


def test_search_detects_hk_market(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=0700.HK")
    items = resp.json()["data"]
    assert items[0]["market"] == "HK"


def test_search_detects_cn_market(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=600519.SS")
    items = resp.json()["data"]
    assert items[0]["market"] == "CN"


def test_search_bare_cn_code_suggests_suffix(initialized_client):
    """输入纯 6 位 A 股代码应提示需要补交易所后缀。"""
    resp = initialized_client.get("/api/v1/search?q=600519")
    items = resp.json()["data"]
    assert len(items) >= 1
    item = items[0]
    assert item["ticker"] == "600519"
    assert item["market"] == "CN"
    assert item["note"] is not None
    assert ".SS" in item["note"]


def test_search_empty_result_is_not_an_error(initialized_client):
    """无结果时返回空列表而非报错（FR-SEARCH-05）。"""
    resp = initialized_client.get("/api/v1/search?q=zzzzzzzznotarealticker")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_search_limit_is_respected(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=a&limit=1")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) <= 1


def test_search_market_filter(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=AAPL&market=CN")
    assert resp.status_code == 200
    for item in resp.json()["data"]:
        assert item["market"] == "CN"


def test_search_response_carries_meta(initialized_client):
    body = initialized_client.get("/api/v1/search?q=AAPL").json()
    assert "source" in body["meta"]
    assert "cached" in body["meta"]


# ----------------------------------------------------------------------
# SearchService 单元测试（不依赖网络）
# ----------------------------------------------------------------------
class _FakeProvider:
    name: ClassVar[str] = "fake"
    markets: ClassVar[set[str]] = {"US", "HK", "CN"}

    def __init__(self, items: list[Instrument]) -> None:
        self._items = items
        self.calls: list[str] = []

    def search(self, query: str) -> list[Instrument]:
        self.calls.append(query)
        return list(self._items)


def _service(items: list[Instrument]):
    from app.providers.cache import TtlCache
    from app.providers.registry import ProviderRegistry
    from app.services.search_service import SearchService

    reg = ProviderRegistry()
    reg.register(_FakeProvider(items), ["US"])
    return SearchService(providers=reg, cache=TtlCache(), demo_mode=False)


def test_search_service_ranks_exact_match_first():

    svc = _service(
        [
            Instrument(ticker="AAPL", name="Apple Inc."),
            Instrument(ticker="AAPL.B", name="Apple something"),
        ]
    )
    results, _ = svc.search("aapl")
    assert results[0].ticker == "AAPL"


def test_search_service_falls_back_to_exact_code_match():
    svc = _service([])
    results, _ = svc.search("tsla")
    assert len(results) == 1
    assert results[0].ticker == "TSLA"
    assert results[0].provider == "local"


def test_search_service_dedupes_by_ticker():
    svc = _service([Instrument(ticker="AAPL", name="Apple Inc.")])
    results, _ = svc.search("apple")
    assert len(results) == 1


def test_search_service_uses_cache_on_second_call():
    svc = _service([Instrument(ticker="AAPL", name="Apple Inc.")])
    svc.search("aapl")
    results, meta = svc.search("aapl")
    assert meta["cached"] is True
    assert results[0].ticker == "AAPL"


def test_search_service_empty_query_returns_empty():
    svc = _service([Instrument(ticker="AAPL", name="Apple Inc.")])
    results, _ = svc.search("   ")
    assert results == []


def test_search_service_local_match_carries_suffix_hint():
    svc = _service([])
    results, _ = svc.search("600519")
    item = results[0]
    assert item.market is Market.CN
    assert item.source_meta.get("suffix_suggestion") == ".SS"
    assert item.kind is InstrumentKind.EQUITY
