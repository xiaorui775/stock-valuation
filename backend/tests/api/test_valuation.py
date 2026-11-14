"""估值接口测试。"""
from __future__ import annotations

import pytest


def test_valuation_requires_auth(client):
    resp = client.get("/api/v1/stocks/AAPL/valuation")
    assert resp.status_code == 401


def test_valuation_returns_dcf(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/valuation")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["dcf"] is not None
    assert data["dcf"]["per_share"] > 0
    assert data["inputs"]["base_fcf"] == 112_000_000_000
    assert data["inputs"]["base_fcf_year"] == 2025


def test_valuation_uses_capm_default_discount(initialized_client):
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    # beta=1.18 → 4 + 1.18*5 = 9.9
    assert data["inputs"]["discount_default_capm"] == pytest.approx(9.9)
    assert data["inputs"]["discount"] == pytest.approx(9.9)


def test_valuation_accepts_overrides(initialized_client):
    resp = initialized_client.get(
        "/api/v1/stocks/AAPL/valuation?growth=5&terminal=2&discount=12&ddm_growth=1"
    )
    inputs = resp.json()["data"]["inputs"]
    assert inputs["growth"] == 5
    assert inputs["terminal"] == 2
    assert inputs["discount"] == 12
    assert inputs["ddm_growth"] == 1


def test_valuation_capm_default_follows_currency(initialized_client):
    """DCF 默认折现率与 WACC 一样按币种预填无风险利率。"""
    data = initialized_client.get(
        "/api/v1/stocks/600519.SS/valuation"
    ).json()["data"]
    # CNY 无风险利率 2.5% + beta 0.68 × 5% = 5.9%
    assert data["inputs"]["discount_default_capm"] == pytest.approx(5.9)
    assert data["sources"]["capm"]["risk_free"] == 2.5
    assert "2.5%" in data["sources"]["capm"]["formula"]


def test_valuation_sensitivity_table(initialized_client):
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    sens = data["sensitivity"]
    assert len(sens["rows"]) == 5
    assert sens["terminal_growths"] == [1.5, 2.5, 3.5]
    # 折现率越高估值越低
    values = [r["values"][1] for r in sens["rows"]]
    assert values == sorted(values, reverse=True)


def test_valuation_multiples_include_formula(initialized_client):
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    names = {m["name"] for m in data["multiples"]}
    assert "P/E（市盈率）" in names
    assert "FCF Yield" in names
    assert all(m["formula"] for m in data["multiples"])


def test_valuation_multiples_order_and_forward_pe(initialized_client):
    """FR-VAL-04：倍数集合包含 Forward P/E，顺序与 PRD 一致。"""
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    names = [m["name"] for m in data["multiples"]]
    assert "Forward P/E（预期市盈率）" in names
    assert names.index("P/E（市盈率）") < names.index("Forward P/E（预期市盈率）")
    assert names.index("Forward P/E（预期市盈率）") < names.index("P/S（市销率）")
    forward = next(m for m in data["multiples"] if m["name"].startswith("Forward"))
    assert forward["value"] == pytest.approx(23.0, rel=0.02)


def test_summary_lists_methods_with_equal_weights(initialized_client):
    """FR-VAL-05：综合结论标注参与方法、各自结果与权重。"""
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    summary = data["summary"]
    assert len(summary["methods"]) == summary["methods_used"]
    assert {m["name"] for m in summary["methods"]} <= {"DCF", "DDM", "Graham"}
    assert sum(m["weight"] for m in summary["methods"]) == pytest.approx(100)
    average = sum(m["value"] for m in summary["methods"]) / len(summary["methods"])
    assert summary["average_value"] == pytest.approx(average)


def test_valuation_ddm_present_with_dividend(initialized_client):
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    assert data["ddm"] is not None
    assert data["ddm"]["per_share"] > 0


def test_valuation_summary_band(initialized_client):
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    summary = data["summary"]
    assert summary is not None
    assert summary["band"] in {"低估", "合理", "高估"}
    assert summary["methods_used"] >= 2


def test_wacc_endpoint(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/valuation/wacc")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["result"] is not None
    assert 0 < data["result"]["wacc"] < 50


def test_wacc_defaults_risk_free_by_currency(initialized_client):
    """FR-VAL-08：无风险利率按币种预填（USD 4.0 / CNY 2.5 / HKD 3.5）。"""
    expected = {"AAPL": 4.0, "600519.SS": 2.5, "0700.HK": 3.5}
    for ticker, risk_free in expected.items():
        data = initialized_client.get(
            f"/api/v1/stocks/{ticker}/valuation/wacc"
        ).json()["data"]
        assert data["inputs"]["risk_free"] == risk_free, ticker


def test_wacc_accepts_custom_inputs(initialized_client):
    data = initialized_client.get(
        "/api/v1/stocks/AAPL/valuation/wacc"
        "?risk_free=3&erp=6&beta=0.8&cost_of_debt=5&tax_rate=25"
    ).json()["data"]
    inputs, result = data["inputs"], data["result"]
    assert inputs["risk_free"] == 3
    assert inputs["erp"] == 6
    assert inputs["beta"] == 0.8
    assert inputs["cost_of_debt"] == 5
    assert inputs["tax_rate"] == 25
    assert result["cost_of_equity"] == pytest.approx(3 + 0.8 * 6)
    expected = (
        result["weight_equity"] * 7.8
        + result["weight_debt"] * 5 * (1 - 0.25)
    )
    assert result["wacc"] == pytest.approx(expected)


def test_scenarios_endpoint(initialized_client):
    resp = initialized_client.post(
        "/api/v1/stocks/AAPL/valuation/scenarios",
        json={
            "scenarios": [
                {"name": "bear", "growth": 0, "terminal": 2.0, "discount": 11, "probability": 25},
                {"name": "base", "growth": 10, "terminal": 2.5, "discount": 9.9, "probability": 50},
                {"name": "bull", "growth": 20, "terminal": 3.0, "discount": 9, "probability": 25},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["scenarios"]) == 3
    assert data["weighted"] is not None


def test_scenarios_weighted_matches_probabilities(initialized_client):
    resp = initialized_client.post(
        "/api/v1/stocks/AAPL/valuation/scenarios",
        json={
            "scenarios": [
                {"name": "bear", "growth": 0, "terminal": 2.0, "discount": 11, "probability": 30},
                {"name": "base", "growth": 10, "terminal": 2.5, "discount": 9.9, "probability": 40},
                {"name": "bull", "growth": 20, "terminal": 3.0, "discount": 9, "probability": 30},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    expected = sum(
        item["per_share"] * item["probability"] for item in data["scenarios"]
    ) / 100
    assert data["weighted"] == pytest.approx(expected)
    assert all(item["upside_pct"] is not None for item in data["scenarios"])


def test_scenarios_reject_bad_probability(initialized_client):
    resp = initialized_client.post(
        "/api/v1/stocks/AAPL/valuation/scenarios",
        json={
            "scenarios": [
                {"name": "base", "growth": 10, "terminal": 2.5, "discount": 9.9, "probability": 50}
            ]
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNPROCESSABLE"


def test_reverse_dcf_endpoint(initialized_client):
    resp = initialized_client.post("/api/v1/stocks/AAPL/valuation/reverse", json={})
    assert resp.status_code == 200
    data = resp.json()["data"]
    # 演示数据下应有解或明确的 reason
    assert data["implied_growth"] is not None or data["reason"]


def test_valuation_accepts_base_fcf_override(initialized_client):
    """用户可覆盖基准 FCF（FR-VAL-01），结果随之变化并标记来源。"""
    base = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    resp = initialized_client.get(
        "/api/v1/stocks/AAPL/valuation?base_fcf=224000000000"
    )
    data = resp.json()["data"]
    assert data["inputs"]["base_fcf"] == 224_000_000_000
    assert data["inputs"]["base_fcf_source"] == "用户输入"
    assert data["sources"]["fcf"]["origin"] == "用户输入"
    assert data["dcf"]["per_share"] > base["dcf"]["per_share"]
    assert data["dcf"]["base_fcf"] == 224_000_000_000


def test_valuation_accepts_years_override(initialized_client):
    data = initialized_client.get(
        "/api/v1/stocks/AAPL/valuation?years1=8"
    ).json()["data"]
    assert data["inputs"]["years1"] == 8


def test_valuation_exposes_assumption_sources(initialized_client):
    """FR-VAL-06：FCF 财年、资产负债表、股本、Beta 与 CAPM 过程都可追溯。"""
    data = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    sources = data["sources"]
    assert sources["fcf"]["year"] == 2025
    assert sources["fcf"]["field"] == "free_cash_flow"
    assert sources["fcf"]["origin"] == "最新年报"
    assert sources["balance"]["origins"]["debt"] == "最新年报"
    assert sources["balance"]["values"]["debt"] == data["inputs"]["total_debt"]
    assert sources["shares"]["value"] == data["inputs"]["shares_outstanding"]
    assert sources["beta"]["value"] == pytest.approx(1.18)
    assert sources["capm"]["value"] == pytest.approx(9.9)
    assert "β" in sources["capm"]["formula"]


def test_valuation_negative_fcf_does_not_crash(initialized_client):
    """负 FCF 是合法输入，返回可解释的结果而不是 500。"""
    resp = initialized_client.get(
        "/api/v1/stocks/AAPL/valuation?base_fcf=-1000000000"
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["inputs"]["base_fcf"] == -1_000_000_000
    assert data["dcf"]["per_share"] is not None
    assert data["dcf"]["per_share"] < 0


def test_valuation_history_endpoint(initialized_client):
    """FR-VAL-11：四个指标都有当前值，3 年与 5 年分位各带五个分位点。"""
    resp = initialized_client.get("/api/v1/stocks/AAPL/valuation/history")
    assert resp.status_code == 200
    data = resp.json()["data"]
    keys = [m["key"] for m in data["metrics"]]
    assert keys == ["pe", "pb", "ps", "fcf_yield"]
    for metric in data["metrics"]:
        assert metric["current"] is not None, metric["key"]
        stats = metric["stats_5y"]
        assert stats is not None, metric["key"]
        assert {"p10", "p25", "p50", "p75", "p90"} <= set(stats)
        assert stats["p10"] <= stats["p50"] <= stats["p90"]
        assert 0 <= metric["percentile_5y"] <= 100
    assert data["windows"]["5y"] < data["windows"]["3y"]


def test_valuation_history_requires_auth(client):
    assert client.get("/api/v1/stocks/AAPL/valuation/history").status_code == 401


def test_valuation_history_unknown_ticker(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/NOPE.XX/valuation/history")
    assert resp.status_code == 404


def test_multistage_endpoint(initialized_client):
    """FR-VAL-12：三阶段 DCF 与 DDM，含阶段分解。"""
    resp = initialized_client.get("/api/v1/stocks/AAPL/valuation/multistage")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["dcf"]["per_share"] > 0
    assert data["assumptions"]["fade_years"] == 5
    assert data["dcf"]["years"] == 10  # 显式 5 年 + 衰减 5 年
    ddm = data["ddm"]
    assert ddm is not None
    parts = ddm["pv_explicit"] + ddm["pv_fade"] + ddm["pv_terminal"]
    assert parts == pytest.approx(ddm["per_share"])


def test_multistage_fade_lowers_dcf(initialized_client):
    """期限对齐后比较：5 年显式 + 5 年衰减，低于 10 年恒定增速。"""
    base = initialized_client.get("/api/v1/stocks/AAPL/valuation/multistage").json()["data"]
    constant = initialized_client.get(
        "/api/v1/stocks/AAPL/valuation/multistage?years1=10&fade_years=0"
    ).json()["data"]
    assert base["dcf"]["years"] == constant["dcf"]["years"] == 10
    assert base["dcf"]["per_share"] < constant["dcf"]["per_share"]


def test_multistage_ddm_absent_without_dividend(initialized_client):
    """没有股息的标的不展示 DDM，并说明原因。"""
    data = initialized_client.get(
        "/api/v1/stocks/TSLA/valuation/multistage"
    ).json()["data"]
    assert data["ddm"] is None
    assert "股息" in data["ddm_reason"]
    assert data["dcf"] is not None


def test_multistage_requires_auth(client):
    assert client.get("/api/v1/stocks/AAPL/valuation/multistage").status_code == 401


def test_summary_weights_endpoint(initialized_client):
    """FR-VAL-13：用户自选方法与权重，结果等于加权平均。"""
    base = initialized_client.get("/api/v1/stocks/AAPL/valuation").json()["data"]
    values = {m["name"]: m["value"] for m in base["summary"]["methods"]}
    selection = [{"name": "DCF", "weight": 80}, {"name": "Graham", "weight": 20}]
    resp = initialized_client.post(
        "/api/v1/stocks/AAPL/valuation/summary", json={"methods": selection}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    expected = values["DCF"] * 0.8 + values["Graham"] * 0.2
    assert data["weighted_value"] == pytest.approx(expected)
    assert data["total_weight"] == pytest.approx(100)
    assert [m["name"] for m in data["methods"]] == ["DCF", "Graham"]
    assert {m["name"] for m in data["available"]} == set(values)


def test_summary_weights_must_total_100(initialized_client):
    resp = initialized_client.post(
        "/api/v1/stocks/AAPL/valuation/summary",
        json={"methods": [{"name": "DCF", "weight": 60}]},
    )
    assert resp.status_code == 422
    assert "100" in resp.json()["error"]["message"]


def test_summary_rejects_unavailable_method(initialized_client):
    resp = initialized_client.post(
        "/api/v1/stocks/AAPL/valuation/summary",
        json={"methods": [{"name": "PE", "weight": 100}]},
    )
    assert resp.status_code == 422
    assert "PE" in resp.json()["error"]["message"]


def test_summary_ddm_unavailable_for_non_payer(initialized_client):
    resp = initialized_client.post(
        "/api/v1/stocks/TSLA/valuation/summary",
        json={"methods": [{"name": "DDM", "weight": 100}]},
    )
    assert resp.status_code == 422
    assert "DDM" in resp.json()["error"]["message"]


def test_valuation_discount_below_terminal_returns_null(initialized_client):
    """折现率 ≤ 永续增速时数学不成立，DCF 返回 null 而不是抛出 500。"""
    resp = initialized_client.get("/api/v1/stocks/AAPL/valuation?discount=2&terminal=2.5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["dcf"] is None
    assert data["inputs"]["discount"] == 2
