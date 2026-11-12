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
