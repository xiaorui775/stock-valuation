"""多股对比接口测试（§5.10）。"""
from __future__ import annotations

import pytest

BASE = "/api/v1/compare"


def _compare(client, tickers: str, period: str = "1y") -> dict:
    resp = client.get(f"{BASE}", params={"tickers": tickers, "period": period})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_compare_requires_auth(client):
    assert client.get(BASE, params={"tickers": "AAPL,MSFT"}).status_code == 401


def test_compare_two_tickers(initialized_client):
    data = _compare(initialized_client, "aapl,msft")
    assert [item["ticker"] for item in data["tickers"]] == ["AAPL", "MSFT"]
    assert len(data["metrics"]) == 14
    assert set(data["series"]) == {"AAPL", "MSFT"}
    assert all(item["currency"] == "USD" for item in data["tickers"])
    assert not any("计价货币不同" in w for w in data["warnings"])


def test_series_is_normalized_to_100(initialized_client):
    data = _compare(initialized_client, "AAPL,MSFT")
    for points in data["series"].values():
        assert points, "走势序列不应为空"
        assert points[0]["value"] == pytest.approx(100)
        assert all(point["value"] > 0 for point in points)


def test_metric_ranking_uses_server_direction(initialized_client):
    data = _compare(initialized_client, "AAPL,MSFT")
    metrics = {row["key"]: row for row in data["metrics"]}
    pe = metrics["pe_ttm"]
    assert pe["direction"] == "lower"
    # 最优 = 更低的 P/E
    assert pe["best"] == min(pe["values"], key=lambda k: pe["values"][k])
    beta = metrics["beta"]
    assert beta["direction"] is None
    assert beta["best"] is None and beta["worst"] is None


def test_mixed_currencies_are_flagged(initialized_client):
    data = _compare(initialized_client, "AAPL,0700.HK")
    currencies = {item["currency"] for item in data["tickers"]}
    assert currencies == {"USD", "HKD"}
    assert any("计价货币不同" in w for w in data["warnings"])


def test_valuation_uses_unified_assumptions(initialized_client):
    data = _compare(initialized_client, "AAPL,MSFT")
    assumptions = data["valuation"]["assumptions"]
    assert assumptions["growth"] == 10
    assert assumptions["years1"] == 5
    assert assumptions["terminal"] == 2.5
    rows = {row["ticker"]: row for row in data["valuation"]["rows"]}
    assert rows["AAPL"]["per_share"] is not None
    assert rows["AAPL"]["price"] is not None


def test_too_few_tickers_rejected(initialized_client):
    resp = initialized_client.get(BASE, params={"tickers": "AAPL"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNPROCESSABLE"


def test_too_many_tickers_rejected(initialized_client):
    resp = initialized_client.get(
        BASE, params={"tickers": "AAPL,MSFT,NVDA,TSLA,AMZN,0700.HK,9988.HK"}
    )
    assert resp.status_code == 422
    assert "6" in resp.json()["error"]["message"]


def test_duplicate_tickers_do_not_count_twice(initialized_client):
    # 去重后只剩 1 只，按「至少 2 只不同标的」拒绝
    resp = initialized_client.get(BASE, params={"tickers": "AAPL,AAPL"})
    assert resp.status_code == 422


def test_one_bad_ticker_does_not_break_the_table(initialized_client):
    data = _compare(initialized_client, "AAPL,ZZZZ")
    columns = {item["ticker"]: item for item in data["tickers"]}
    assert columns["AAPL"]["error"] is None
    assert columns["ZZZZ"]["error"]
    assert any("ZZZZ" in w for w in data["warnings"])
    assert data["series"]["AAPL"]
