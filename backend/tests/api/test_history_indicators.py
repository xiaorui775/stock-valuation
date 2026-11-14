"""历史行情技术指标接口测试（演示模式，FR-CHART-03）。

指标随 `/stocks/{ticker}/history` 返回，序列与 bars 按下标对齐。
"""
from __future__ import annotations

INDICATOR_KEYS = (
    "ma5", "ma10", "ma20", "ma60", "ma120",
    "boll_mid", "boll_upper", "boll_lower",
    "dif", "dea", "macd", "rsi14",
)


def _history(client, ticker="AAPL", period="1y", interval="1d"):
    resp = client.get(
        f"/api/v1/stocks/{ticker}/history?period={period}&interval={interval}"
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_history_includes_indicator_series(initialized_client):
    data = _history(initialized_client)
    indicators = data["indicators"]
    for key in INDICATOR_KEYS:
        assert key in indicators, key
        assert len(indicators[key]) == data["count"], key


def test_indicators_null_before_window(initialized_client):
    data = _history(initialized_client, period="1y")
    indicators = data["indicators"]
    # 一年日线 252 根：MA5 前 4 个位置窗口不满
    assert all(v is None for v in indicators["ma5"][:4])
    assert indicators["ma5"][4] is not None
    # MA120 前 119 个为 None
    assert all(v is None for v in indicators["ma120"][:119])
    assert indicators["ma120"][119] is not None
    # RSI 前 14 个为 None
    assert all(v is None for v in indicators["rsi14"][:14])
    assert indicators["rsi14"][14] is not None


def test_ma_values_match_bruteforce(initialized_client):
    data = _history(initialized_client, period="6mo")
    closes = [bar["close"] for bar in data["bars"]]
    ma20 = data["indicators"]["ma20"]
    for i in range(len(closes)):
        if i >= 19:
            expected = sum(closes[i - 19 : i + 1]) / 20
            assert ma20[i] == approx(expected)
        else:
            assert ma20[i] is None


def approx(x):
    import pytest

    return pytest.approx(x)


def test_boll_and_macd_consistent(initialized_client):
    data = _history(initialized_client, period="1y")
    ind = data["indicators"]
    for i in range(len(data["bars"])):
        mid, upper, lower = ind["boll_mid"][i], ind["boll_upper"][i], ind["boll_lower"][i]
        if mid is not None:
            assert upper > mid > lower
        dif, dea, hist = ind["dif"][i], ind["dea"][i], ind["macd"][i]
        if dif is not None and dea is not None:
            assert hist == approx((dif - dea) * 2)


def test_rsi_bounds(initialized_client):
    data = _history(initialized_client, period="max")
    values = [v for v in data["indicators"]["rsi14"] if v is not None]
    assert values
    assert all(0 <= v <= 100 for v in values)


def test_weekly_history_has_indicators(initialized_client):
    data = _history(initialized_client, period="1y", interval="1wk")
    assert len(data["indicators"]["ma20"]) == data["count"]
