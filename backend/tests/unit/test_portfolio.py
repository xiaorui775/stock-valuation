"""组合汇总纯计算测试（FR-PORT-03 / 04 / 07）。"""
from __future__ import annotations

import pytest

from app.analysis.portfolio import HoldingRow, holding_metrics, summarize

BASE = "CNY"


def row(**overrides) -> HoldingRow:
    defaults = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "market": "US",
        "currency": "USD",
        "quantity": 10.0,
        "avg_cost": 100.0,
        "price": 120.0,
        "previous_close": 118.0,
        "fx_rate": 7.0,
        "dcf_upside_pct": None,
    }
    defaults.update(overrides)
    return HoldingRow(**defaults)


def test_positive_unrealized_profit():
    metrics = holding_metrics(row())
    assert metrics["market_value_local"] == pytest.approx(1200)
    assert metrics["market_value"] == pytest.approx(8400)
    assert metrics["cost"] == pytest.approx(7000)
    assert metrics["unrealized_pnl"] == pytest.approx(1400)
    assert metrics["unrealized_pnl_pct"] == pytest.approx(20)
    assert metrics["day_pnl"] == pytest.approx((120 - 118) * 10 * 7)
    assert metrics["converted"] is True


def test_negative_unrealized_profit():
    metrics = holding_metrics(row(price=80.0, avg_cost=100.0))
    assert metrics["unrealized_pnl"] == pytest.approx(-1400)
    assert metrics["unrealized_pnl_pct"] == pytest.approx(-20)


def test_zero_quantity_has_no_percentage():
    metrics = holding_metrics(row(quantity=0.0))
    assert metrics["market_value"] == 0
    assert metrics["cost"] == 0
    assert metrics["unrealized_pnl"] == 0
    assert metrics["unrealized_pnl_pct"] is None


def test_missing_fx_keeps_local_value_but_no_base_value():
    metrics = holding_metrics(row(fx_rate=None))
    assert metrics["converted"] is False
    assert metrics["market_value_local"] == pytest.approx(1200)
    assert metrics["market_value"] is None
    assert metrics["cost"] is None
    assert metrics["unrealized_pnl"] is None


def test_missing_price_gives_no_value():
    metrics = holding_metrics(row(price=None))
    assert metrics["market_value_local"] is None
    assert metrics["market_value"] is None
    assert metrics["converted"] is False


def test_empty_portfolio_totals_are_zero_not_none():
    result = summarize([], BASE)
    assert result["total_market_value"] == 0
    assert result["unrealized_pnl"] == 0
    assert result["rows"] == []
    assert result["warnings"] == []


def test_all_rows_unconverted_yields_none_totals():
    result = summarize([row(fx_rate=None)], BASE)
    assert result["total_market_value"] is None
    assert result["unconverted"][0]["currency"] == "USD"
    assert result["unconverted"][0]["market_value_local"] == pytest.approx(1200)
    assert any("缺少" in w for w in result["warnings"])
    assert any("无法计算组合汇总" in w for w in result["warnings"])


def test_weights_sum_to_100_for_converted_rows():
    result = summarize([row(quantity=10), row(ticker="MSFT", quantity=30)], BASE)
    weights = [r["weight_pct"] for r in result["rows"]]
    assert sum(weights) == pytest.approx(100)
    assert weights[0] == pytest.approx(25)
    assert weights[1] == pytest.approx(75)


def test_unconverted_row_has_no_weight_and_does_not_break_weights():
    result = summarize([row(quantity=10), row(ticker="MSFT", currency="EUR", fx_rate=None)], BASE)
    assert result["rows"][1]["weight_pct"] is None
    assert sum(r["weight_pct"] for r in result["rows"] if r["weight_pct"] is not None) == pytest.approx(100)
    assert [u["currency"] for u in result["unconverted"]] == ["EUR"]


def test_concentration_warning_above_threshold():
    result = summarize([row(quantity=90), row(ticker="MSFT", quantity=10)], BASE)
    assert [c["ticker"] for c in result["concentration"]] == ["AAPL"]
    assert any("集中度" in w for w in result["warnings"])


def test_concentration_threshold_is_strict():
    # 50% 不超过 50% 阈值，不应触发提示
    result = summarize(
        [row(quantity=10), row(ticker="MSFT", quantity=10)],
        BASE,
        concentration_pct=50,
    )
    assert result["concentration"] == []


def test_market_distribution_and_weighted_upside():
    result = summarize(
        [
            row(quantity=10, market="US", dcf_upside_pct=50),
            row(ticker="600519.SS", name="贵州茅台", market="CN", currency="CNY",
                quantity=30, fx_rate=1.0, dcf_upside_pct=-10),
        ],
        BASE,
    )
    weights = {d["market"]: d["weight_pct"] for d in result["distribution"]}
    # AAPL 10×120×7 = 8400 CNY；茅台 30×120×1 = 3600 CNY
    assert weights["US"] == pytest.approx(70)
    assert weights["CN"] == pytest.approx(30)
    assert result["weighted_upside_pct"] == pytest.approx(0.7 * 50 + 0.3 * -10)
    assert result["upside_coverage_pct"] == pytest.approx(100)


def test_weighted_upside_coverage_reports_partial():
    result = summarize(
        [row(quantity=10, dcf_upside_pct=30), row(ticker="MSFT", quantity=30)],
        BASE,
    )
    assert result["weighted_upside_pct"] == pytest.approx(30)
    assert result["upside_coverage_pct"] == pytest.approx(25)


def test_day_pnl_missing_when_previous_close_absent():
    result = summarize([row(previous_close=None)], BASE)
    assert result["rows"][0]["day_pnl"] is None
    assert result["day_pnl"] is None
    assert result["day_pnl_pct"] is None


def test_unpriced_rows_are_reported():
    result = summarize([row(), row(ticker="MSFT", price=None)], BASE)
    assert any("缺少可用行情" in w for w in result["warnings"])
