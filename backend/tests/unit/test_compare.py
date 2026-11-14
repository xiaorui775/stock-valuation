"""多股对比纯计算测试（§5.10）。"""
from __future__ import annotations

import pytest

from app.analysis.compare import HIGHER, LOWER, best_worst, normalize_series


def test_higher_is_better():
    best, worst = best_worst({"A": 5, "B": 9, "C": 3}, HIGHER)
    assert (best, worst) == ("B", "C")


def test_lower_is_better():
    best, worst = best_worst({"A": 5, "B": 9, "C": 3}, LOWER)
    assert (best, worst) == ("C", "B")


def test_missing_values_do_not_win_or_lose():
    best, worst = best_worst({"A": None, "B": 9, "C": 3}, HIGHER)
    assert (best, worst) == ("B", "C")


def test_single_value_has_no_ranking():
    assert best_worst({"A": 5, "B": None}, HIGHER) == (None, None)


def test_all_equal_has_no_ranking():
    assert best_worst({"A": 5, "B": 5}, LOWER) == (None, None)


def test_no_direction_has_no_ranking():
    assert best_worst({"A": 5, "B": 9}, None) == (None, None)


def test_ties_resolve_to_the_first_value_seen():
    best, worst = best_worst({"A": 9, "B": 9, "C": 3}, HIGHER)
    assert best == "A"
    assert worst == "C"


def test_normalize_series_starts_at_100():
    series = normalize_series([("2026-01-02", 50.0), ("2026-01-03", 55.0)])
    assert series[0] == {"date": "2026-01-02", "value": 100.0}
    assert series[1]["value"] == pytest.approx(110.0)


def test_normalize_series_empty_or_zero_base():
    assert normalize_series([]) == []
    assert normalize_series([("2026-01-02", 0.0)]) == []
