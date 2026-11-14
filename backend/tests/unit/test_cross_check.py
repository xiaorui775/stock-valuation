"""交叉校验（FR-DATA-04）单元测试。"""
from __future__ import annotations

from app.analysis.cross_check import cross_check_annual, cross_check_revenue


def test_cross_check_revenue_none_when_missing():
    assert cross_check_revenue(None, None) is None
    assert cross_check_revenue(100.0, None) is None
    assert cross_check_revenue(None, 100.0) is None
    assert cross_check_revenue(0, 100.0) is None


def test_cross_check_revenue_in_range_is_not_conflict():
    # TTM 略高于年报属正常口径差异
    result = cross_check_revenue(172_054_171_890.91, 174_433_934_764.98)
    assert result is not None
    assert result["conflict"] is False
    assert 0.5 <= result["ratio"] <= 2.0
    assert result["field"] == "revenue"


def test_cross_check_revenue_out_of_range_is_conflict():
    result = cross_check_revenue(100.0, 300.0)
    assert result is not None
    assert result["conflict"] is True
    assert result["ratio"] == 3.0


def test_cross_check_revenue_negative_denominator_uses_abs():
    result = cross_check_revenue(-100.0, -150.0)
    assert result is not None
    assert result["diff_pct"] == -50.0  # 相对年报的方向保留


def test_cross_check_annual_missing_returns_none():
    assert cross_check_annual(None, 100.0, "revenue", "a", "b") is None
    assert cross_check_annual(100.0, None, "revenue", "a", "b") is None


def test_cross_check_annual_within_threshold():
    result = cross_check_annual(100.0, 101.0, "revenue", "akshare", "sina")
    assert result is not None
    assert result["conflict"] is False


def test_cross_check_annual_conflict_over_two_percent():
    result = cross_check_annual(100.0, 110.0, "revenue", "akshare", "sina")
    assert result is not None
    assert result["conflict"] is True
    assert result["diff_pct"] == 10.0
    assert "差异" in result["note"]
