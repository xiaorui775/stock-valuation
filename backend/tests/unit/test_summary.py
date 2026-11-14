"""加权综合估值：纯计算（FR-VAL-13）。"""
from __future__ import annotations

import pytest

from app.valuation.summary import BAND_THRESHOLD, band_for, combine


def test_equal_weights_match_average():
    result = combine([("DCF", 100.0, 50.0), ("Graham", 200.0, 50.0)], price=150.0)
    assert result is not None
    assert result["average_value"] == pytest.approx(150.0)
    assert result["vs_price_pct"] == pytest.approx(0.0)
    assert result["band"] == "合理"


def test_custom_weights():
    result = combine([("DCF", 100.0, 90.0), ("Graham", 200.0, 10.0)], price=100.0)
    assert result is not None
    assert result["average_value"] == pytest.approx(110.0)
    assert result["vs_price_pct"] == pytest.approx(10.0)
    assert sum(m["contribution"] for m in result["methods"]) == pytest.approx(110.0)


def test_weights_must_sum_to_100():
    assert combine([("DCF", 100.0, 60.0), ("Graham", 200.0, 30.0)], price=100.0) is None
    # 允许 100 ± 0.05 的舍入误差
    assert combine(
        [("A", 1.0, 33.3), ("B", 1.0, 33.3), ("C", 1.0, 33.4)], price=1.0
    ) is not None


def test_negative_weight_rejected():
    assert combine([("DCF", 100.0, 120.0), ("Graham", 200.0, -20.0)], price=100.0) is None


def test_empty_selection():
    assert combine([], price=100.0) is None


def test_band_thresholds():
    assert band_for(BAND_THRESHOLD + 1) == "低估"
    assert band_for(-BAND_THRESHOLD - 1) == "高估"
    assert band_for(0) == "合理"
    assert band_for(None) is None


def test_missing_price_keeps_value_but_no_band():
    result = combine([("DCF", 100.0, 100.0)], price=None)
    assert result is not None
    assert result["average_value"] == pytest.approx(100.0)
    assert result["vs_price_pct"] is None
    assert result["band"] is None
