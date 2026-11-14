"""规则化财务解读的单元测试：每条规则的正例、反例与边界（§5.6）。"""
from __future__ import annotations

from app.analysis.financial_insights import analyze
from app.providers.models import FinancialYear, Quote


def y(year: int, **fields) -> FinancialYear:
    return FinancialYear(year=year, **fields)


def items(result: dict) -> dict[str, dict]:
    return {item["rule"]: item for item in result["items"]}


def uncovered(result: dict) -> set[str]:
    return {item["rule"] for item in result["uncovered"]}


def quote(**fields) -> Quote:
    return Quote(ticker="X", name="X", price=10.0, **fields)


# ---- 营收增长 ---------------------------------------------------------
def test_revenue_growth_high_is_info():
    result = analyze([y(2025, revenue=130), y(2024, revenue=100)])
    assert items(result)["revenue_growth"]["level"] == "info"


def test_revenue_decline_is_watch():
    result = analyze([y(2025, revenue=90), y(2024, revenue=100)])
    assert items(result)["revenue_growth"]["level"] == "watch"


def test_revenue_growth_normal_does_not_trigger():
    result = analyze([y(2025, revenue=110), y(2024, revenue=100)])
    assert "revenue_growth" not in items(result)


def test_revenue_growth_boundary_is_exclusive():
    """恰好 20% 不触发（规则是 > 20）。"""
    result = analyze([y(2025, revenue=120), y(2024, revenue=100)])
    assert "revenue_growth" not in items(result)


def test_revenue_growth_includes_cagr_when_available():
    years = [
        y(2025, revenue=200),
        y(2024, revenue=150),
        y(2023, revenue=120),
        y(2022, revenue=100),
    ]
    item = items(analyze(years))["revenue_growth"]
    assert "CAGR" in item["detail"]


# ---- 利润率趋势 -------------------------------------------------------
def test_gross_margin_decline_triggers():
    years = [
        y(2025, revenue=1000, gross_profit=400),
        y(2024, revenue=1000, gross_profit=430),
        y(2023, revenue=1000, gross_profit=450),
    ]
    assert items(analyze(years))["gross_margin_trend"]["level"] == "watch"


def test_gross_margin_decline_within_threshold():
    years = [
        y(2025, revenue=1000, gross_profit=445),
        y(2024, revenue=1000, gross_profit=447),
        y(2023, revenue=1000, gross_profit=450),
    ]
    # 累计下降 0.5pp，不触发
    assert "gross_margin_trend" not in items(analyze(years))


def test_gross_margin_not_monotonic():
    years = [
        y(2025, revenue=1000, gross_profit=460),
        y(2024, revenue=1000, gross_profit=440),
        y(2023, revenue=1000, gross_profit=450),
    ]
    assert "gross_margin_trend" not in items(analyze(years))


def test_operating_margin_trend():
    years = [
        y(2025, revenue=1000, operating_income=200),
        y(2024, revenue=1000, operating_income=230),
        y(2023, revenue=1000, operating_income=250),
    ]
    assert items(analyze(years))["operating_margin_trend"]["level"] == "watch"


def test_net_margin_trend():
    years = [
        y(2025, revenue=1000, net_income=100),
        y(2024, revenue=1000, net_income=130),
        y(2023, revenue=1000, net_income=150),
    ]
    assert items(analyze(years))["net_margin_trend"]["level"] == "watch"


# ---- 现金流质量 / 应计 ------------------------------------------------
def test_cash_quality_alert():
    years = [
        y(2025, net_income=100, free_cash_flow=30),
        y(2024, net_income=90, free_cash_flow=40),
    ]
    assert items(analyze(years))["cash_quality"]["level"] == "alert"


def test_cash_quality_boundary_50_percent():
    years = [
        y(2025, net_income=100, free_cash_flow=50),
        y(2024, net_income=90, free_cash_flow=45),
    ]
    assert "cash_quality" not in items(analyze(years))


def test_cash_quality_skips_negative_income():
    years = [
        y(2025, net_income=-10, free_cash_flow=5),
        y(2024, net_income=-5, free_cash_flow=1),
    ]
    assert "cash_quality" in uncovered(analyze(years))


def test_accrual_anomaly_alert():
    years = [
        y(2025, net_income=130, operating_cash_flow=100),
        y(2024, net_income=100, operating_cash_flow=100),
    ]
    assert items(analyze(years))["accrual_anomaly"]["level"] == "alert"


def test_accrual_anomaly_boundary():
    """差额恰好 20pp 不触发（规则是 > 20）。"""
    years = [
        y(2025, net_income=120, operating_cash_flow=100),
        y(2024, net_income=100, operating_cash_flow=100),
    ]
    assert "accrual_anomaly" not in items(analyze(years))


# ---- 杠杆 / 稀释 ------------------------------------------------------
def test_leverage_debt_to_equity():
    result = analyze([y(2025, total_debt=300, total_equity=100)])
    assert items(result)["leverage"]["level"] == "watch"


def test_leverage_debt_to_equity_boundary():
    result = analyze([y(2025, total_debt=200, total_equity=100)])
    assert "leverage" not in items(result)


def test_leverage_net_debt_to_ebitda():
    years = [y(2025, total_debt=600, total_cash=100, total_equity=400)]
    result = analyze(years, quote(ebitda=100))
    assert "净债务 / EBITDA" in items(result)["leverage"]["detail"]


def test_leverage_skips_negative_equity():
    years = [y(2025, total_debt=300, total_equity=-50)]
    result = analyze(years)
    assert "leverage" in uncovered(result)


def test_dilution_triggers():
    years = [
        y(2025, shares_outstanding=105),
        y(2024, shares_outstanding=100),
    ]
    assert items(analyze(years))["dilution"]["level"] == "watch"


def test_dilution_boundary():
    years = [
        y(2025, shares_outstanding=102),
        y(2024, shares_outstanding=100),
    ]
    assert "dilution" not in items(analyze(years))


# ---- 毛利率扩张 / 应收存货 --------------------------------------------
def test_gross_margin_expansion_is_info():
    years = [
        y(2025, revenue=1000, gross_profit=450),
        y(2024, revenue=1000, gross_profit=410),
    ]
    assert items(analyze(years))["gross_margin_expansion"]["level"] == "info"


def test_gross_margin_expansion_boundary():
    years = [
        y(2025, revenue=1000, gross_profit=440),
        y(2024, revenue=1000, gross_profit=410),
    ]
    assert "gross_margin_expansion" not in items(analyze(years))


def test_receivables_growth_triggers():
    years = [
        y(2025, revenue=130, accounts_receivable=160),
        y(2024, revenue=100, accounts_receivable=100),
    ]
    assert items(analyze(years))["receivables_inventory"]["level"] == "watch"


def test_inventory_growth_triggers():
    years = [
        y(2025, revenue=110, inventory=150),
        y(2024, revenue=100, inventory=100),
    ]
    assert items(analyze(years))["receivables_inventory"]["level"] == "watch"


def test_receivables_rule_skipped_without_fields():
    years = [y(2025, revenue=130), y(2024, revenue=100)]
    assert "receivables_inventory" in uncovered(analyze(years))


# ---- 汇总行为 ---------------------------------------------------------
def test_items_sorted_by_severity():
    years = [
        y(2025, revenue=130, net_income=100, free_cash_flow=30),
        y(2024, revenue=100, net_income=90, free_cash_flow=40),
    ]
    result = analyze(years)
    levels = [item["level"] for item in result["items"]]
    assert levels == sorted(levels, key=["alert", "watch", "info"].index)
    assert result["items"][0]["level"] == "alert"


def test_summary_when_nothing_triggers():
    result = analyze([y(2025, revenue=110), y(2024, revenue=105)])
    assert result["items"] == []
    assert result["summary"] == "未发现显著异常。"


def test_no_years_is_insufficient():
    result = analyze([])
    assert result["items"] == []
    assert result["uncovered"][0]["rule"] == "all"
    assert "没有可用" in result["summary"]


def test_single_year_still_evaluates_leverage():
    """只有一年数据时，单年可算的规则（如杠杆）仍然会执行。"""
    result = analyze([y(2025, total_debt=300, total_equity=100)])
    assert items(result)["leverage"]["level"] == "watch"
    assert "revenue_growth" in uncovered(result)


def test_analysis_is_deterministic():
    years = [
        y(2025, revenue=130, net_income=100, free_cash_flow=30),
        y(2024, revenue=100, net_income=90, free_cash_flow=40),
    ]
    assert analyze(years) == analyze(years)
