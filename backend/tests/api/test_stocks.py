"""行情与财务接口测试（演示模式，不联网）。"""
from __future__ import annotations

from typing import ClassVar


def test_quote_requires_auth(client):
    resp = client.get("/api/v1/stocks/AAPL/quote")
    assert resp.status_code == 401


def test_quote_returns_data(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/quote")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["ticker"] == "AAPL"
    assert body["data"]["price"] == 182.50
    assert body["meta"]["source"] == "demo"
    assert body["meta"]["currency"] == "USD"


def test_quote_reports_source_and_demo_flag(initialized_client):
    """演示模式不经过缓存，meta.source 应为 demo。"""
    resp = initialized_client.get("/api/v1/stocks/AAPL/quote")
    assert resp.json()["meta"]["source"] == "demo"
    assert resp.json()["meta"]["cached"] is False


def test_history_caches_second_call(initialized_client, monkeypatch):
    """非演示模式下，第二次请求应命中缓存。"""
    from app.providers.cache import TtlCache
    from app.services.market_service import MarketService

    service = MarketService(cache=TtlCache())
    monkeypatch.setattr(service, "demo_mode", False)

    calls = {"n": 0}

    class FakeProvider:
        name: ClassVar[str] = "fake"
        markets: ClassVar[set[str]] = {"US"}

        def get_history(self, ticker, period="1y", interval="1d"):
            calls["n"] += 1
            from datetime import date

            from app.providers.models import Bar

            return [Bar(date=date(2026, 1, 1), close=100.0)]

    from app.providers.registry import ProviderRegistry

    reg = ProviderRegistry()
    reg.register(FakeProvider(), ["US"])

    service.registry = reg
    bars1, meta1 = service.get_history("AAPL")
    bars2, meta2 = service.get_history("AAPL")

    assert calls["n"] == 1
    assert meta1["cached"] is False
    assert meta2["cached"] is True


def test_history_returns_bars(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/history?period=6mo&interval=1d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["period"] == "6mo"
    assert len(body["data"]["bars"]) > 100
    assert body["data"]["bars"][0]["close"] is not None


def test_history_rejects_bad_period_by_falling_back(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/history?period=bogus")
    assert resp.status_code == 200
    assert resp.json()["data"]["period"] == "1y"


def test_financials_returns_five_years(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/financials")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]["years"]) == 5
    assert body["data"]["years"][0]["year"] == 2025
    assert body["data"]["years"][0]["free_cash_flow"] == 112_000_000_000


def test_financials_limit_is_respected(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/financials?limit=2")
    assert len(resp.json()["data"]["years"]) == 2


def test_news_returns_items(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/news")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 2


def test_news_kind_filter(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/news?kind=announcement")
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["kind"] == "announcement"


def test_search_returns_instrument(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=AAPL")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 1
    assert items[0]["ticker"] == "AAPL"


def test_search_requires_query(initialized_client):
    resp = initialized_client.get("/api/v1/search?q=")
    assert resp.status_code == 422
