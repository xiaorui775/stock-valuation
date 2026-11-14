"""历史行情接口测试（演示模式，不联网）。

覆盖 FR-CHART-01（周期）、FR-CHART-05（数据区间/复权提示/不插值）与周月线聚合。
"""
from __future__ import annotations


def _history(client, ticker="AAPL", period="1y", interval="1d"):
    resp = client.get(
        f"/api/v1/stocks/{ticker}/history?period={period}&interval={interval}"
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_history_exposes_range_and_adjustment(initialized_client):
    data = _history(initialized_client, period="6mo")
    bars = data["bars"]
    assert data["count"] == len(bars)
    assert data["start_date"] == bars[0]["date"]
    assert data["end_date"] == bars[-1]["date"]
    assert data["adjustment"] == "前复权"
    assert data["interval"] == "1d"


def test_history_period_lengths(initialized_client):
    """各周期返回的日线条数符合交易日折算。"""
    expected = {"1mo": 22, "3mo": 66, "6mo": 130, "1y": 252, "max": 2520}
    for period, count in expected.items():
        data = _history(initialized_client, period=period)
        assert data["count"] == count, period


def test_history_max_period_is_supported(initialized_client):
    """MAX 周期此前会被演示数据源忽略（FR-CHART-01）。"""
    data = _history(initialized_client, period="max")
    assert data["period"] == "max"
    assert data["count"] > 2000


def test_history_skips_weekends(initialized_client):
    """合成的交易日不落在周末，避免图表出现数据源没有的日期。"""
    from datetime import date

    for bar in _history(initialized_client, period="1mo")["bars"]:
        assert date.fromisoformat(bar["date"]).weekday() < 5


def test_history_last_close_matches_quote(initialized_client):
    quote = initialized_client.get("/api/v1/stocks/AAPL/quote").json()["data"]
    bars = _history(initialized_client, period="1y")["bars"]
    assert bars[-1]["close"] == quote["price"]


def test_history_ohlc_is_consistent(initialized_client):
    for bar in _history(initialized_client, period="3mo")["bars"]:
        assert bar["high"] >= max(bar["open"], bar["close"])
        assert bar["low"] <= min(bar["open"], bar["close"])
        assert bar["volume"] is not None


def test_history_weekly_aggregation(initialized_client):
    from datetime import date

    daily = _history(initialized_client, period="1y", interval="1d")["bars"]
    weekly = _history(initialized_client, period="1y", interval="1wk")["bars"]

    # 一年约 52 周，允许跨年边界上下浮动
    assert 50 <= len(weekly) <= 54
    assert len(weekly) < len(daily)

    assert weekly[0]["open"] == daily[0]["open"]
    assert weekly[-1]["close"] == daily[-1]["close"]
    assert [b["date"] for b in weekly] == sorted(b["date"] for b in weekly)

    # 最后一根周线只包含同一 ISO 周的日线（当周可能不完整）
    last_week = date.fromisoformat(daily[-1]["date"]).isocalendar()[:2]
    group = [
        b
        for b in daily
        if date.fromisoformat(b["date"]).isocalendar()[:2] == last_week
    ]
    assert weekly[-1]["high"] == max(b["high"] for b in group)
    assert weekly[-1]["low"] == min(b["low"] for b in group)
    assert weekly[-1]["volume"] == sum(b["volume"] for b in group)


def test_history_monthly_aggregation(initialized_client):
    monthly = _history(initialized_client, period="1y", interval="1mo")["bars"]
    assert 12 <= len(monthly) <= 14
    months = [b["date"][:7] for b in monthly]
    assert len(set(months)) == len(months), "每根月线应覆盖不同月份"


def test_history_invalid_interval_falls_back(initialized_client):
    data = _history(initialized_client, interval="5m")
    assert data["interval"] == "1d"


def test_history_unknown_ticker_returns_404(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/ZZZZ/history")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TICKER_NOT_FOUND"


def test_history_requires_auth(client):
    assert client.get("/api/v1/stocks/AAPL/history").status_code == 401
