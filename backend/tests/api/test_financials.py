"""年度财务报表接口测试：同比、3 年 CAGR、缺失项（FR-FIN-01/03/04）。"""
from __future__ import annotations

import pytest


def _financials(client, query: str = ""):
    resp = client.get(f"/api/v1/stocks/AAPL/financials{query}")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_financials_contains_all_fields(initialized_client):
    data = _financials(initialized_client)
    year = data["years"][0]
    for field in (
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "eps",
        "operating_cash_flow",
        "capex",
        "free_cash_flow",
        "total_debt",
        "total_cash",
        "total_equity",
        "shares_outstanding",
    ):
        assert year[field] is not None, field
    assert data["currency"] == "USD"


def test_financials_yoy_uses_absolute_denominator(initialized_client):
    data = _financials(initialized_client)
    years = data["years"]
    latest, previous = years[0], years[1]
    # 最新财年对齐画像收入（AAPL 4,160 亿），同比由该序列计算
    assert latest["revenue"] == pytest.approx(416_000_000_000)
    expected = (
        (latest["revenue"] - previous["revenue"]) / abs(previous["revenue"]) * 100
    )
    assert latest["yoy"]["revenue"] == pytest.approx(expected, rel=1e-9)
    third = years[2]
    assert previous["yoy"]["revenue"] == pytest.approx(
        (previous["revenue"] - third["revenue"]) / third["revenue"] * 100, rel=1e-9
    )


def test_financials_oldest_year_has_no_yoy(initialized_client):
    """最早一期没有上期，同比一律为 null，不填 0。"""
    data = _financials(initialized_client)
    oldest = data["years"][-1]
    assert oldest["year"] == 2021
    assert all(value is None for value in oldest["yoy"].values())


def test_financials_cagr_three_years(initialized_client):
    data = _financials(initialized_client)
    latest, base = data["years"][0], data["years"][3]
    expected = ((latest["revenue"] / base["revenue"]) ** (1 / 3) - 1) * 100
    assert data["cagr_years"] == 3
    assert data["cagr"]["revenue"] == pytest.approx(expected, rel=1e-9)


def test_financials_cagr_absent_with_too_few_years(initialized_client):
    data = _financials(initialized_client, "?limit=3")
    assert len(data["years"]) == 3
    assert data["cagr"] == {}


def test_financials_missing_fields_is_empty_for_complete_data(initialized_client):
    assert _financials(initialized_client)["missing_fields"] == []


def test_financials_unknown_ticker_returns_404(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/ZZZZ/financials")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TICKER_NOT_FOUND"
