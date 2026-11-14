"""投资组合接口测试（FR-PORT-01 / 02 / 03 / 04 / 07）。"""
from __future__ import annotations

import pytest

BASE = "/api/v1/portfolios"


def _default_portfolio(client) -> dict:
    return client.get(BASE).json()["data"]["items"][0]


def test_portfolios_require_auth(client):
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json={"name": "x"}).status_code == 401


def test_first_list_creates_default_portfolio(initialized_client):
    data = initialized_client.get(BASE).json()["data"]
    assert len(data["items"]) == 1
    portfolio = data["items"][0]
    assert portfolio["name"] == "我的组合"
    assert portfolio["base_currency"] == "CNY"
    assert portfolio["holding_count"] == 0
    assert portfolio["holdings"] == []


def test_create_update_and_delete_portfolio(initialized_client):
    initialized_client.get(BASE)
    created = initialized_client.post(
        BASE, json={"name": "长期账户", "base_currency": "USD", "note": "美股为主"}
    )
    assert created.status_code == 201, created.text
    portfolio = created.json()["data"]
    assert portfolio["base_currency"] == "USD"
    assert portfolio["note"] == "美股为主"

    renamed = initialized_client.patch(
        f"{BASE}/{portfolio['id']}", json={"name": "长期价值", "base_currency": "HKD"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["name"] == "长期价值"
    assert renamed.json()["data"]["base_currency"] == "HKD"

    deleted = initialized_client.delete(f"{BASE}/{portfolio['id']}")
    assert deleted.status_code == 200
    names = [p["name"] for p in initialized_client.get(BASE).json()["data"]["items"]]
    assert "长期价值" not in names


def test_duplicate_portfolio_name_conflicts(initialized_client):
    initialized_client.get(BASE)
    resp = initialized_client.post(BASE, json={"name": "我的组合"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_unsupported_currency_rejected(initialized_client):
    resp = initialized_client.post(BASE, json={"name": "日元账户", "base_currency": "JPY"})
    assert resp.status_code == 422


def test_add_holding_uses_quote_metadata(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    resp = initialized_client.post(
        f"{BASE}/{portfolio['id']}/holdings",
        json={"ticker": "aapl", "quantity": 10, "avg_cost": 150, "note": "首批"},
    )
    assert resp.status_code == 201, resp.text
    holding = resp.json()["data"]
    assert holding["ticker"] == "AAPL"
    assert holding["name"] == "Apple Inc."
    assert holding["market"] == "US"
    assert holding["currency"] == "USD"
    assert holding["quantity"] == 10
    assert holding["avg_cost"] == 150
    assert holding["note"] == "首批"


def test_holding_currency_can_be_overridden(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    resp = initialized_client.post(
        f"{BASE}/{portfolio['id']}/holdings",
        json={"ticker": "AAPL", "quantity": 1, "avg_cost": 100, "currency": "CNY"},
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["currency"] == "CNY"


def test_duplicate_holding_conflicts(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    body = {"ticker": "AAPL", "quantity": 1, "avg_cost": 100}
    assert initialized_client.post(f"{BASE}/{portfolio['id']}/holdings", json=body).status_code == 201
    again = initialized_client.post(f"{BASE}/{portfolio['id']}/holdings", json=body)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "CONFLICT"


def test_invalid_ticker_returns_404_and_is_not_saved(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    resp = initialized_client.post(
        f"{BASE}/{portfolio['id']}/holdings",
        json={"ticker": "ZZZZ", "quantity": 1, "avg_cost": 1},
    )
    assert resp.status_code == 404
    holdings = initialized_client.get(f"{BASE}/{portfolio['id']}/holdings").json()["data"]
    assert holdings == []


def test_negative_quantity_rejected(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    resp = initialized_client.post(
        f"{BASE}/{portfolio['id']}/holdings",
        json={"ticker": "AAPL", "quantity": -1, "avg_cost": 100},
    )
    assert resp.status_code == 422


def test_update_and_delete_holding(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    holding = initialized_client.post(
        f"{BASE}/{portfolio['id']}/holdings",
        json={"ticker": "AAPL", "quantity": 10, "avg_cost": 150},
    ).json()["data"]

    updated = initialized_client.patch(
        f"{BASE}/{portfolio['id']}/holdings/{holding['id']}",
        json={"quantity": 25.5, "avg_cost": 160.25, "opened_on": "2026-03-01", "note": "加仓"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()["data"]
    assert body["quantity"] == 25.5
    assert body["avg_cost"] == 160.25
    assert body["opened_on"] == "2026-03-01"
    assert body["note"] == "加仓"

    deleted = initialized_client.delete(
        f"{BASE}/{portfolio['id']}/holdings/{holding['id']}"
    )
    assert deleted.status_code == 200
    assert initialized_client.get(f"{BASE}/{portfolio['id']}/holdings").json()["data"] == []


def test_deleting_portfolio_removes_holdings(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    initialized_client.post(
        f"{BASE}/{portfolio['id']}/holdings",
        json={"ticker": "AAPL", "quantity": 1, "avg_cost": 100},
    )
    assert initialized_client.delete(f"{BASE}/{portfolio['id']}").status_code == 200
    # 组合已删除，其持仓接口返回 404，而不是残留数据
    assert initialized_client.get(f"{BASE}/{portfolio['id']}/holdings").status_code == 404


def test_unknown_portfolio_returns_404(initialized_client):
    assert initialized_client.get(f"{BASE}/9999").status_code == 404
    assert initialized_client.patch(f"{BASE}/9999", json={"name": "x"}).status_code == 404
    assert initialized_client.delete(f"{BASE}/9999").status_code == 404
    assert initialized_client.get(f"{BASE}/9999/holdings").status_code == 404
    assert initialized_client.get(f"{BASE}/9999/summary").status_code == 404


# ----------------------------------------------------------------------
# 组合汇总（FR-PORT-03 / 04 / 07）
# ----------------------------------------------------------------------


def test_summary_requires_auth(client):
    assert client.get(f"{BASE}/1/summary").status_code == 401


def test_summary_of_empty_portfolio(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    data = initialized_client.get(f"{BASE}/{portfolio['id']}/summary").json()["data"]
    assert data["total_market_value"] == 0
    assert data["unrealized_pnl"] == 0
    assert data["rows"] == []
    assert data["warnings"] == []


def test_summary_converts_multi_currency_holdings(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    pid = portfolio["id"]
    for body in (
        {"ticker": "AAPL", "quantity": 10, "avg_cost": 150},
        {"ticker": "0700.HK", "quantity": 100, "avg_cost": 300},
    ):
        assert initialized_client.post(f"{BASE}/{pid}/holdings", json=body).status_code == 201

    resp = initialized_client.get(f"{BASE}/{pid}/summary")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    rows = {row["ticker"]: row for row in data["rows"]}
    assert set(rows) == {"AAPL", "0700.HK"}

    # 汇率是演示数据里的固定值：USD/CNY 7.10、HKD/CNY 0.91
    rates = {item["currency"]: item["rate"] for item in data["fx_rates"]}
    assert rates["CNY"] == 1.0
    assert rates["USD"] == pytest.approx(7.10)
    assert rates["HKD"] == pytest.approx(0.91)

    expected_total = (
        rows["AAPL"]["price"] * 10 * 7.10 + rows["0700.HK"]["price"] * 100 * 0.91
    )
    expected_cost = 150 * 10 * 7.10 + 300 * 100 * 0.91
    assert data["total_market_value"] == pytest.approx(expected_total)
    assert data["total_cost"] == pytest.approx(expected_cost)
    assert data["unrealized_pnl"] == pytest.approx(expected_total - expected_cost)
    assert data["unrealized_pnl_pct"] == pytest.approx(
        (expected_total - expected_cost) / expected_cost * 100
    )
    assert sum(row["weight_pct"] for row in data["rows"]) == pytest.approx(100)
    assert data["day_pnl"] is not None
    assert data["weighted_upside_pct"] is not None


def test_summary_uses_identity_rate_for_base_currency(initialized_client):
    """持仓币种不在汇率表内时不换算，按币种分组并提示。"""
    portfolio = _default_portfolio(initialized_client)
    pid = portfolio["id"]
    created = initialized_client.post(
        f"{BASE}/{pid}/holdings",
        json={"ticker": "AAPL", "quantity": 10, "avg_cost": 150, "currency": "CNY"},
    )
    assert created.status_code == 201
    data = initialized_client.get(f"{BASE}/{pid}/summary").json()["data"]
    # CNY 持仓换算回 CNY 是恒等，不应产生分组
    assert data["unconverted"] == []
    assert data["fx_rates"][0]["source"] == "identity"
    assert data["unrealized_pnl"] is not None


def test_summary_converts_single_foreign_currency(initialized_client):
    portfolio = _default_portfolio(initialized_client)
    pid = portfolio["id"]
    initialized_client.post(
        f"{BASE}/{pid}/holdings",
        json={"ticker": "AAPL", "quantity": 10, "avg_cost": 150, "currency": "HKD"},
    )
    data = initialized_client.get(f"{BASE}/{pid}/summary").json()["data"]
    # 港币持仓用 HKD/CNY 汇率换算，仍属于可换算范围
    assert data["rows"][0]["fx_rate"] == pytest.approx(0.91)
    assert data["unconverted"] == []
