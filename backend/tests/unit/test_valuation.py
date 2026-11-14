"""估值模型单元测试：golden case 与边界。"""
from __future__ import annotations

import pytest

from app.valuation.dcf import dcf_three_stage, dcf_value
from app.valuation.ddm import ddm_value
from app.valuation.graham import graham_number
from app.valuation.multiples import fcf_yield, safe_div
from app.valuation.reverse_dcf import implied_growth
from app.valuation.scenarios import build_scenarios
from app.valuation.wacc import capm_discount_rate, default_risk_free, wacc


class TestDCF:
    def test_two_stage_golden_case(self):
        """手工验算：FCF=100, g=10%/5年, r=10%, gT=2.5%, 股数=1。

        显式期现值 = Σ 100×1.1^t / 1.1^t = 500
        终值 = 161.051×1.025/0.075 = 2200.36；折现 5 年 → 1365.20
        每股价值 ≈ 1865.20
        """
        res = dcf_value(
            base_fcf=100.0, growth1_pct=10.0, years1=5,
            terminal_growth_pct=2.5, discount_pct=10.0,
            total_debt=0, total_cash=0, shares=1.0,
        )
        assert res is not None
        expected_pv = sum(100 * 1.1 ** t / 1.1 ** t for t in range(1, 6))
        fcf5 = 100 * 1.1 ** 5
        tv = fcf5 * 1.025 / 0.075
        expected = expected_pv + tv / 1.1 ** 5
        assert res["per_share"] == pytest.approx(expected, rel=1e-9)
        assert res["per_share"] == pytest.approx(1866.6667, rel=1e-4)

    def test_returns_none_when_shares_missing(self):
        assert dcf_value(100.0, 10, 5, 2.5, 10, 0, 0, None) is None
        assert dcf_value(100.0, 10, 5, 2.5, 10, 0, 0, 0) is None

    def test_returns_none_when_base_fcf_missing(self):
        assert dcf_value(None, 10, 5, 2.5, 10, 0, 0, 100) is None

    def test_returns_none_when_discount_le_terminal(self):
        assert dcf_value(100.0, 10, 5, 5.0, 5.0, 0, 0, 100) is None

    def test_debt_and_cash_adjust_equity(self):
        with_debt = dcf_value(100.0, 10, 5, 2.5, 10, 50, 0, 10)
        with_cash = dcf_value(100.0, 10, 5, 2.5, 10, 0, 50, 10)
        assert with_debt["equity_value"] == with_cash["equity_value"] - 100

    def test_terminal_ratio_between_zero_and_one(self):
        res = dcf_value(100.0, 10, 5, 2.5, 10, 0, 0, 10)
        assert 0 < res["pv_terminal_ratio"] < 1

    def test_three_stage_equals_two_stage_when_no_fade(self):
        three = dcf_three_stage(100.0, 10, 5, 0, 2.5, 10, 0, 0, 10)
        two = dcf_value(100.0, 10, 5, 2.5, 10, 0, 0, 10)
        assert three["per_share"] == pytest.approx(two["per_share"], rel=1e-9)

    def test_three_stage_with_fade_lower_than_two_stage(self):
        """衰减期增速低于恒定增速时，同期限内估值应更低。

        比较必须对齐期限：三阶段为 5 年显式 + 5 年衰减 = 10 年，
        因此对照两阶段的 10 年显式期版本。
        """
        three = dcf_three_stage(100.0, 15, 5, 5, 2.5, 10, 0, 0, 10)
        two_same_horizon = dcf_value(100.0, 15, 10, 2.5, 10, 0, 0, 10)
        assert three["per_share"] < two_same_horizon["per_share"]


class TestDDM:
    def test_gordon_golden_case(self):
        # 股价 100, 股息率 2%, g=3%, r=8% → DPS=2, V = 2*1.03/0.05 = 41.2
        val = ddm_value(100.0, 2.0, 3.0, 8.0)
        assert val == pytest.approx(41.2)

    def test_none_when_no_dividend(self):
        assert ddm_value(100.0, 0, 3.0, 8.0) is None
        assert ddm_value(100.0, None, 3.0, 8.0) is None

    def test_none_when_discount_le_growth(self):
        assert ddm_value(100.0, 2.0, 8.0, 8.0) is None


class TestGraham:
    def test_graham_number(self):
        # √(22.5 * 10 * 5) = √1125 ≈ 33.54
        assert graham_number(10.0, 5.0) == pytest.approx(33.5410196625, rel=1e-6)

    def test_none_for_negative_or_missing(self):
        assert graham_number(-1.0, 5.0) is None
        assert graham_number(10.0, -5.0) is None
        assert graham_number(None, 5.0) is None


class TestMultiples:
    def test_safe_div(self):
        assert safe_div(10, 2) == 5.0
        assert safe_div(10, 0) is None
        assert safe_div(None, 2) is None

    def test_fcf_yield(self):
        assert fcf_yield(10.0, 100.0) == pytest.approx(10.0)
        assert fcf_yield(10.0, None) is None


class TestWACC:
    def test_capm(self):
        assert capm_discount_rate(1.5) == pytest.approx(11.5)
        assert capm_discount_rate(None) == pytest.approx(9.0)

    def test_wacc_known_case(self):
        # E=1000, D=500, rf=4%, beta=1, erp=5% → r_e=9%; rd=6%, t=21%
        # WACC = 2/3*9 + 1/3*6*0.79 = 6 + 1.58 = 7.58
        res = wacc(4.0, 1.0, 5.0, 6.0, 21.0, 500.0, 1000.0)
        assert res["wacc"] == pytest.approx(7.58)
        assert res["cost_of_equity"] == pytest.approx(9.0)
        assert res["weight_equity"] == pytest.approx(2 / 3)

    def test_wacc_none_when_inputs_missing(self):
        assert wacc(4.0, 1.0, 5.0, 6.0, 21.0, None, 1000.0) is None
        assert wacc(4.0, 1.0, 5.0, 6.0, 21.0, 500.0, None) is None

    def test_default_risk_free_by_currency(self):
        assert default_risk_free("USD") == 4.0
        assert default_risk_free("CNY") == 2.5
        assert default_risk_free(None) == 4.0
        assert default_risk_free("XYZ") == 4.0


class TestReverseDCF:
    def test_solves_implied_growth(self):
        """给定 DCF 结果作为目标价格，反解增速应还原原增速。"""
        target_growth = 12.0
        forward = dcf_value(
            100.0, target_growth, 5, 2.5, 10.0, 0, 0, 10.0
        )
        price = forward["per_share"]
        res = implied_growth(
            price, 100.0, 5, 2.5, 10.0, 0, 0, 10.0
        )
        assert res is not None
        assert res["implied_growth"] == pytest.approx(target_growth, abs=0.05)

    def test_none_when_price_unreachable(self):
        """现价高于最大增速下的估值时无解。"""
        res = implied_growth(1e12, 100.0, 5, 2.5, 10.0, 0, 0, 10.0)
        assert res is not None
        assert res["implied_growth"] is None
        assert res["reason"]

    def test_none_when_missing_inputs(self):
        assert implied_growth(None, 100.0, 5, 2.5, 10.0, 0, 0, 10.0) is None
        assert implied_growth(100.0, None, 5, 2.5, 10.0, 0, 0, 10.0) is None


class TestScenarios:
    def test_weighted_average(self):
        result = build_scenarios(
            100.0,
            [
                {"name": "bear", "growth": 0, "terminal": 2.0, "discount": 11, "probability": 25},
                {"name": "base", "growth": 10, "terminal": 2.5, "discount": 10, "probability": 50},
                {"name": "bull", "growth": 20, "terminal": 3.0, "discount": 9, "probability": 25},
            ],
            0, 0, 10.0, 100.0,
        )
        assert result["error"] is None
        assert len(result["scenarios"]) == 3
        # 加权期望应落在 bear 与 bull 之间
        assert result["weighted"] > result["scenarios"][0]["per_share"]
        assert result["weighted"] < result["scenarios"][2]["per_share"]

    def test_probability_must_sum_to_100(self):
        result = build_scenarios(
            100.0,
            [{"name": "base", "growth": 10, "terminal": 2.5, "discount": 10, "probability": 50}],
            0, 0, 10.0, 100.0,
        )
        assert result["error"] is not None
        assert result["weighted"] is None

    def test_scenario_value_ordering(self):
        result = build_scenarios(
            100.0,
            [
                {"name": "bear", "growth": 0, "terminal": 2.0, "discount": 11, "probability": 50},
                {"name": "bull", "growth": 20, "terminal": 3.0, "discount": 9, "probability": 50},
            ],
            0, 0, 10.0, 100.0,
        )
        assert result["scenarios"][1]["per_share"] > result["scenarios"][0]["per_share"]
