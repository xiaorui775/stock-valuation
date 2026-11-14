"""筛选器纯计算测试（§5.11）。"""
from __future__ import annotations

from app.analysis.screener import Filter, paginate, passes, sort_rows


def test_no_filters_passes_everything():
    assert passes({"pe_ttm": 10}, []) is True
    assert passes({"pe_ttm": None}, []) is True


def test_min_and_max_bounds():
    rule = Filter("pe_ttm", minimum=10, maximum=20)
    assert passes({"pe_ttm": 15}, [rule]) is True
    assert passes({"pe_ttm": 10}, [rule]) is True
    assert passes({"pe_ttm": 20}, [rule]) is True
    assert passes({"pe_ttm": 9.99}, [rule]) is False
    assert passes({"pe_ttm": 20.01}, [rule]) is False


def test_missing_value_never_passes_a_bounded_filter():
    rule = Filter("pe_ttm", maximum=20)
    assert passes({"pe_ttm": None}, [rule]) is False
    assert passes({}, [rule]) is False


def test_all_rules_must_pass():
    rules = [Filter("pe_ttm", maximum=20), Filter("dividend_yield", minimum=1)]
    assert passes({"pe_ttm": 15, "dividend_yield": 2}, rules) is True
    assert passes({"pe_ttm": 15, "dividend_yield": 0.5}, rules) is False
    assert passes({"pe_ttm": 25, "dividend_yield": 2}, rules) is False


def test_sort_ascending_puts_missing_last():
    rows = [{"t": "A", "v": 3}, {"t": "B", "v": None}, {"t": "C", "v": 1}]
    assert [row["t"] for row in sort_rows(rows, "v", False)] == ["C", "A", "B"]


def test_sort_descending_puts_missing_last():
    rows = [{"t": "A", "v": 3}, {"t": "B", "v": None}, {"t": "C", "v": 1}]
    assert [row["t"] for row in sort_rows(rows, "v", True)] == ["A", "C", "B"]


def test_sort_is_stable_for_ties():
    rows = [{"t": "A", "v": 1}, {"t": "B", "v": 1}]
    assert [row["t"] for row in sort_rows(rows, "v", False)] == ["A", "B"]


def test_sort_without_key_keeps_order():
    rows = [{"t": "A", "v": 3}, {"t": "B", "v": 1}]
    assert sort_rows(rows, None, True) is rows


def test_paginate():
    rows = [{"i": i} for i in range(5)]
    assert [row["i"] for row in paginate(rows, 1, 2)] == [0, 1]
    assert [row["i"] for row in paginate(rows, 3, 2)] == [4]
    assert paginate(rows, 4, 2) == []
    assert paginate(rows, 0, 2) == [{"i": 0}, {"i": 1}]
