"""预设指数与筛选预设接口测试（M2-13）。"""
from __future__ import annotations

BASE = "/api/v1/screener"

POOL = {"pool": {"kind": "custom", "tickers": ["AAPL", "MSFT"]}}


def test_indexes_require_auth(client):
    assert client.get(f"{BASE}/indexes").status_code == 401


def test_list_indexes_seeds_snapshot(initialized_client):
    data = initialized_client.get(f"{BASE}/indexes").json()["data"]
    keys = {item["key"] for item in data}
    assert keys == {"sp500", "csi300", "hsi"}
    sp500 = next(item for item in data if item["key"] == "sp500")
    assert sp500["count"] == 20
    assert sp500["source"] == "内置快照"
    # 快照日期而不是「现在」，避免假装新鲜
    assert sp500["updated_at"].startswith("2026-06-30")


def test_index_detail_returns_members(initialized_client):
    data = initialized_client.get(f"{BASE}/indexes/hsi").json()["data"]
    assert data["label"] == "恒生指数"
    tickers = [member["ticker"] for member in data["members"]]
    assert tickers[:2] == ["0700.HK", "9988.HK"]


def test_unknown_index_returns_404(initialized_client):
    resp = initialized_client.get(f"{BASE}/indexes/nasdaq")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_refresh_without_provider_support_keeps_snapshot(initialized_client):
    resp = initialized_client.post(f"{BASE}/indexes/sp500/refresh")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["refreshed"] is False
    assert "内置快照" in data["reason"]
    assert data["count"] == 20
    assert data["source"] == "内置快照"


def test_screener_accepts_index_pool(initialized_client):
    resp = initialized_client.post(
        BASE,
        json={
            "pool": {"kind": "index", "index_key": "sp500"},
            "filters": [{"metric": "pe_ttm", "max": 30}],
            "page_size": 10,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # 快照 20 只里只有演示数据覆盖的 5 只美股可取数，其余进入 failures
    assert data["requested"] == 20
    assert data["succeeded"] == 5
    assert data["failed"] == 15
    assert data["total"] == len(data["rows"])


def test_index_pool_requires_key(initialized_client):
    resp = initialized_client.post(BASE, json={"pool": {"kind": "index"}})
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# 筛选预设
# ----------------------------------------------------------------------


def test_presets_require_auth(client):
    assert client.get(f"{BASE}/presets").status_code == 401


def test_preset_crud(initialized_client):
    payload = {
        **POOL,
        "filters": [{"metric": "pe_ttm", "max": 30}],
        "sort_key": "pe_ttm",
        "page_size": 20,
    }
    created = initialized_client.post(
        f"{BASE}/presets", json={"name": "低估值美股", "payload": payload}
    )
    assert created.status_code == 201, created.text
    preset = created.json()["data"]
    assert preset["name"] == "低估值美股"
    assert preset["payload"]["filters"][0]["metric"] == "pe_ttm"
    assert preset["payload"]["pool"]["tickers"] == ["AAPL", "MSFT"]

    listed = initialized_client.get(f"{BASE}/presets").json()["data"]
    assert [item["name"] for item in listed] == ["低估值美股"]

    updated = initialized_client.patch(
        f"{BASE}/presets/{preset['id']}",
        json={"name": "低估值美股 v2", "payload": {**payload, "page_size": 50}},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "低估值美股 v2"
    assert updated.json()["data"]["payload"]["page_size"] == 50

    deleted = initialized_client.delete(f"{BASE}/presets/{preset['id']}")
    assert deleted.status_code == 200
    assert initialized_client.get(f"{BASE}/presets").json()["data"] == []


def test_duplicate_preset_name_conflicts(initialized_client):
    body = {"name": "同名", "payload": POOL}
    assert initialized_client.post(f"{BASE}/presets", json=body).status_code == 201
    again = initialized_client.post(f"{BASE}/presets", json=body)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "CONFLICT"


def test_unknown_preset_returns_404(initialized_client):
    assert initialized_client.delete(f"{BASE}/presets/9999").status_code == 404
    assert (
        initialized_client.patch(f"{BASE}/presets/9999", json={"name": "x"}).status_code
        == 404
    )
