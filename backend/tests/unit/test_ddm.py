"""三阶段 DDM：纯计算（FR-VAL-12）。"""
from __future__ import annotations

import pytest

from app.valuation.ddm import ddm_three_stage, ddm_value


def test_requires_dividend():
    assert ddm_three_stage(100.0, 0.0, 10, 5, 5, 2.5, 10) is None
    assert ddm_three_stage(100.0, None, 10, 5, 5, 2.5, 10) is None
    assert ddm_three_stage(None, 2.0, 10, 5, 5, 2.5, 10) is None


def test_rejects_discount_not_above_terminal():
    assert ddm_three_stage(100.0, 2.0, 10, 5, 5, 2.5, 2.5) is None


def test_no_fade_matches_manual_two_stage():
    """衰减期 0 年时就是「显式增长 + Gordon 终值」的两阶段股利模型。"""
    price, dy, g1, years, gt, r = 100.0, 2.0, 8.0, 3, 2.5, 10.0
    result = ddm_three_stage(price, dy, g1, years, 0, gt, r)
    assert result is not None
    dps = price * dy / 100
    expected = 0.0
    dividend = dps
    for t in range(1, years + 1):
        dividend = dps * (1 + g1 / 100) ** t
        expected += dividend / (1 + r / 100) ** t
    expected += (dividend * (1 + gt / 100) / (r / 100 - gt / 100)) / (1 + r / 100) ** years
    assert result["per_share"] == pytest.approx(expected)


def test_fade_lowers_value_versus_same_horizon_constant_growth():
    """衰减期 vs 同期限恒定增速：期限对齐后，衰减的估值更低。

    三阶段是 5 年显式 + 5 年衰减 = 10 年，对照必须是 10 年显式期，
    否则只是比较期限长短，不是在比较衰减。
    """
    with_fade = ddm_three_stage(100.0, 2.0, 15, 5, 5, 2.5, 10)
    constant = ddm_three_stage(100.0, 2.0, 15, 10, 0, 2.5, 10)
    assert with_fade is not None and constant is not None
    assert with_fade["per_share"] < constant["per_share"]
    assert with_fade["years"] == constant["years"] == 10


def test_components_sum_to_per_share():
    result = ddm_three_stage(100.0, 2.0, 12, 5, 5, 2.5, 10)
    assert result is not None
    parts = result["pv_explicit"] + result["pv_fade"] + result["pv_terminal"]
    assert parts == pytest.approx(result["per_share"])
    assert result["pv_fade"] > 0
    assert 0 < result["terminal_ratio"] < 1


def test_matches_gordon_when_no_growth_difference():
    """growth == terminal 且无衰减期时，结果应与 Gordon 模型一致。"""
    price, dy, r, g = 100.0, 4.0, 10.0, 3.0
    gordon = ddm_value(price, dy, g, r)
    staged = ddm_three_stage(price, dy, g, 1, 0, g, r)
    assert gordon is not None and staged is not None
    # 两阶段把第一年单独折现，结果略低于纯 Gordon，但量级一致
    assert staged["per_share"] == pytest.approx(gordon, rel=0.05)
