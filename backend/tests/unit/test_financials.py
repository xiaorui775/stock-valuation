"""财务报表展示层纯函数测试：同比与 CAGR 的边界（FR-FIN-04）。"""
from __future__ import annotations

import pytest

from app.providers.models import Financials, FinancialYear
from app.services.financials_service import build_view, cagr_pct, yoy_pct


def test_yoy_pct_basic():
    assert yoy_pct(110, 100) == pytest.approx(10.0)
    assert yoy_pct(90, 100) == pytest.approx(-10.0)


def test_yoy_pct_uses_absolute_denominator():
    """上期为负时，分母取绝对值——否则亏损收窄会被算成 -50%。"""
    assert yoy_pct(-50, -100) == pytest.approx(50.0)


def test_yoy_pct_returns_none_when_not_computable():
    assert yoy_pct(None, 100) is None
    assert yoy_pct(100, None) is None
    assert yoy_pct(100, 0) is None


def test_cagr_pct_basic():
    expected = (1.5 ** (1 / 3) - 1) * 100
    assert cagr_pct(150, 100, 3) == pytest.approx(expected)


def test_cagr_pct_rejects_non_positive_base():
    assert cagr_pct(150, 0, 3) is None
    assert cagr_pct(150, -100, 3) is None
    assert cagr_pct(-10, 100, 3) is None


def test_build_view_marks_missing_and_orders_newest_first():
    years = [
        FinancialYear(year=2023, revenue=100.0, net_income=None, total_debt=0.0),
        FinancialYear(year=2024, revenue=120.0, net_income=10.0, total_debt=5.0),
    ]
    view = build_view(Financials(ticker="X", currency="USD", years=years))

    assert [y["year"] for y in view["years"]] == [2024, 2023]
    assert view["years"][0]["yoy"]["revenue"] == pytest.approx(20.0)
    assert view["years"][1]["yoy"]["revenue"] is None
    # 缺失科目全部列出，且不参与同比
    assert "net_income" in view["missing_fields"]
    assert view["years"][0]["yoy"]["net_income"] is None


def test_build_view_without_enough_years_has_no_cagr():
    view = build_view(
        Financials(ticker="X", years=[FinancialYear(year=2024, revenue=120.0)])
    )
    assert view["cagr"] == {}
    assert view["cagr_years"] == 3
