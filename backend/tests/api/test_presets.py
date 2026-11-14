"""估值预设接口测试（FR-VAL-07）。"""
from __future__ import annotations

BASE = "/api/v1/stocks"


def _create(client, ticker: str = "AAPL", name: str = "保守假设", **assumptions):
    payload = {
        "name": name,
        "assumptions": {
            "growth": 5,
            "terminal": 2.0,
            "discount": 11,
            **assumptions,
        },
    }
    return client.post(f"{BASE}/{ticker}/valuation/presets", json=payload)


def test_presets_require_auth(client):
    assert client.get(f"{BASE}/AAPL/valuation/presets").status_code == 401


def test_create_and_list_preset(initialized_client):
    resp = _create(initialized_client)
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["ticker"] == "AAPL"
    assert body["name"] == "保守假设"
    assert body["assumptions"]["growth"] == 5
    assert body["assumptions"]["base_fcf"] is None

    listed = initialized_client.get(f"{BASE}/AAPL/valuation/presets").json()["data"]["items"]
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_duplicate_name_returns_409(initialized_client):
    assert _create(initialized_client).status_code == 201
    resp = _create(initialized_client)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_update_preset_name_and_assumptions(initialized_client):
    preset = _create(initialized_client).json()["data"]
    resp = initialized_client.patch(
        f"{BASE}/AAPL/valuation/presets/{preset['id']}",
        json={"name": "乐观假设", "assumptions": {"growth": 15, "terminal": 3.0}},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["name"] == "乐观假设"
    assert data["assumptions"]["growth"] == 15
    assert data["assumptions"]["discount"] is None


def test_rename_to_existing_name_conflicts(initialized_client):
    _create(initialized_client, name="A")
    preset = _create(initialized_client, name="B").json()["data"]
    resp = initialized_client.patch(
        f"{BASE}/AAPL/valuation/presets/{preset['id']}", json={"name": "A"}
    )
    assert resp.status_code == 409


def test_delete_preset(initialized_client):
    preset = _create(initialized_client).json()["data"]
    resp = initialized_client.delete(f"{BASE}/AAPL/valuation/presets/{preset['id']}")
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] is True

    listed = initialized_client.get(f"{BASE}/AAPL/valuation/presets").json()["data"]["items"]
    assert listed == []

    again = initialized_client.delete(f"{BASE}/AAPL/valuation/presets/{preset['id']}")
    assert again.status_code == 404


def test_preset_is_scoped_to_ticker(initialized_client):
    preset = _create(initialized_client, ticker="AAPL").json()["data"]
    other = initialized_client.get(f"{BASE}/MSFT/valuation/presets").json()["data"]["items"]
    assert other == []

    resp = initialized_client.patch(
        f"{BASE}/MSFT/valuation/presets/{preset['id']}", json={"name": "改名"}
    )
    assert resp.status_code == 404


def test_missing_preset_returns_404(initialized_client):
    resp = initialized_client.patch(
        f"{BASE}/AAPL/valuation/presets/99999", json={"name": "x"}
    )
    assert resp.status_code == 404


def test_invalid_assumptions_are_rejected(initialized_client):
    resp = _create(initialized_client, growth=500)
    assert resp.status_code == 422


def test_preset_names_are_trimmed_and_required(initialized_client):
    resp = _create(initialized_client, name="   ")
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# 预设对比（FR-RESEARCH-02）
# ----------------------------------------------------------------------
def _compare(client, ticker: str, ids: list[int] | None = None):
    params = [("ids", str(i)) for i in ids] if ids is not None else None
    return client.get(f"{BASE}/{ticker}/valuation/presets/compare", params=params)


def test_compare_requires_two_presets(initialized_client):
    _create(initialized_client, name="只有一个")
    resp = _compare(initialized_client, "AAPL")
    assert resp.status_code == 422


def test_compare_returns_effective_assumptions_and_results(initialized_client):
    conservative = _create(
        initialized_client, name="保守", growth=3, terminal=2.0, discount=12
    ).json()["data"]
    optimistic = _create(
        initialized_client, name="乐观", growth=15, terminal=3.0, discount=9
    ).json()["data"]

    resp = _compare(initialized_client, "AAPL", [conservative["id"], optimistic["id"]])
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["ticker"] == "AAPL"
    assert data["price"] is not None
    assert data["notes"]
    assert [item["name"] for item in data["items"]] == ["保守", "乐观"]

    low, high = data["items"]
    assert low["growth"] == 3
    assert low["discount"] == 12
    assert high["growth"] == 15
    assert high["discount"] == 9
    assert low["per_share"] is not None and high["per_share"] is not None
    # 更高增速 + 更低折现率必然得到更高的 DCF 每股价值
    assert high["per_share"] > low["per_share"]
    assert high["upside_pct"] > low["upside_pct"]


def test_compare_without_ids_uses_all_presets(initialized_client):
    _create(initialized_client, name="A")
    _create(initialized_client, name="B", growth=8)
    resp = _compare(initialized_client, "AAPL")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 2


def test_compare_unknown_or_foreign_preset_returns_404(initialized_client):
    preset = _create(initialized_client, ticker="AAPL").json()["data"]
    other = _create(initialized_client, ticker="MSFT", name="微软预设").json()["data"]

    resp = _compare(initialized_client, "AAPL", [preset["id"], other["id"]])
    assert resp.status_code == 404
    assert "预设不存在" in resp.json()["error"]["message"]

    missing = _compare(initialized_client, "AAPL", [preset["id"], 99999])
    assert missing.status_code == 404


def test_compare_caps_at_six_presets(initialized_client):
    ids = []
    for index in range(7):
        ids.append(
            _create(initialized_client, name=f"预设{index}", growth=5 + index).json()["data"]["id"]
        )
    resp = _compare(initialized_client, "AAPL", ids)
    assert resp.status_code == 422
