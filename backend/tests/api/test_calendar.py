"""财报日历接口测试（FR-RESEARCH-04）。"""
from __future__ import annotations

BASE = "/api/v1/stocks"


def test_calendar_requires_auth(client):
    assert client.get(f"{BASE}/AAPL/calendar").status_code == 401


def test_calendar_returns_next_earnings_and_source(initialized_client):
    resp = initialized_client.get(f"{BASE}/AAPL/calendar")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = body["data"]
    meta = body["meta"]

    assert data["ticker"] == "AAPL"
    assert data["earnings_date"] is not None
    assert data["days_until_earnings"] is not None
    # 演示数据源给的是今天 + 21 天；按交易所时区计算允许 ±1 天
    assert 20 <= data["days_until_earnings"] <= 22
    assert data["note"] is None
    assert meta["source"] == "demo"
    assert meta["cached"] is False


def test_calendar_rejects_unknown_ticker(initialized_client):
    resp = initialized_client.get(f"{BASE}/ZZZZ/calendar")
    assert resp.status_code == 404


def test_watchlist_quotes_include_earnings_date(initialized_client):
    groups = initialized_client.get("/api/v1/watchlists").json()["data"]["groups"]
    group_id = groups[0]["id"]
    initialized_client.post(
        f"/api/v1/watchlists/{group_id}/items", json={"ticker": "AAPL"}
    )

    resp = initialized_client.get(f"/api/v1/watchlists/{group_id}/quotes")
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]["items"]
    row = next(item for item in rows if item["ticker"] == "AAPL")
    assert row["earnings_date"] is not None
    assert 20 <= row["days_until_earnings"] <= 22
    assert row["earnings_source"] == "demo"
