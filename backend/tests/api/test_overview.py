"""个股概览接口测试。"""
from __future__ import annotations


def test_overview_requires_auth(client):
    resp = client.get("/api/v1/stocks/AAPL/overview")
    assert resp.status_code == 401


def test_overview_returns_quote_head(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/overview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ticker"] == "AAPL"
    assert data["price"] == 182.50
    assert data["currency"] == "USD"
    assert data["market"] == "US"
    assert data["market_label"] == "美股"


def test_overview_includes_session(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/overview")
    session = resp.json()["data"]["session"]
    assert session is not None
    assert session["label"] in {"盘前", "盘中", "盘后", "休市"}
    assert session["timezone"] == "America/New_York"


def test_overview_includes_week52_position(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/overview")
    w52 = resp.json()["data"]["week52"]
    assert w52 is not None
    # 现价 182.50 在 124.17 – 199.62 之间
    assert w52["position"] is not None
    assert 0 <= w52["position"] <= 1


def test_overview_includes_conclusion(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/overview")
    conclusion = resp.json()["data"]["conclusion"]
    assert conclusion is not None
    assert conclusion["dcf_per_share"] is not None
    assert conclusion["band"] in {"低估", "合理", "高估"}
    assert conclusion["methods_used"] >= 1


def test_overview_carries_meta(initialized_client):
    body = initialized_client.get("/api/v1/stocks/AAPL/overview").json()
    assert body["meta"]["source"] == "demo"


def test_overview_unknown_ticker_returns_404(initialized_client):
    """无效代码不返回任何模拟数据（FR-SEARCH-05 延伸）。"""
    resp = initialized_client.get("/api/v1/stocks/NOPEZZZZ/overview")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TICKER_NOT_FOUND"
