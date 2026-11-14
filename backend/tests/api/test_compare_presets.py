"""常用对比组合与口径标注测试（FR-RESEARCH-06）。"""
from __future__ import annotations

BASE = "/api/v1/compare/presets"


def _create(client, name="核心对比", tickers=None):
    return client.post(
        BASE,
        json={"name": name, "tickers": tickers or ["AAPL", "MSFT"]},
    )


def test_compare_presets_require_auth(client):
    assert client.get(BASE).status_code == 401
    assert _create(client).status_code == 401


def test_create_and_list_compare_preset(initialized_client):
    resp = _create(initialized_client, tickers=["aapl", "MSFT", "AAPL"])
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["name"] == "核心对比"
    # 规范化 + 去重，保持首次出现顺序
    assert body["tickers"] == ["AAPL", "MSFT"]

    listed = initialized_client.get(BASE).json()["data"]["items"]
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_compare_preset_duplicate_name_returns_409(initialized_client):
    assert _create(initialized_client).status_code == 201
    resp = _create(initialized_client)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_compare_preset_validation(initialized_client):
    assert _create(initialized_client, tickers=["AAPL"]).status_code == 422
    assert _create(
        initialized_client,
        tickers=["AAPL", "MSFT", "GOOG", "AMZN", "META", "NVDA", "TSLA"],
    ).status_code == 422
    # 去重后不足 2 只
    assert _create(initialized_client, tickers=["AAPL", "aapl"]).status_code == 422
    assert _create(initialized_client, name="   ").status_code == 422


def test_update_and_delete_compare_preset(initialized_client):
    preset = _create(initialized_client).json()["data"]

    resp = initialized_client.patch(
        f"{BASE}/{preset['id']}",
        json={"name": "半导体对比", "tickers": ["NVDA", "AMD"]},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["name"] == "半导体对比"
    assert updated["tickers"] == ["NVDA", "AMD"]

    _create(initialized_client, name="另一组", tickers=["GOOG", "META"])
    conflict = initialized_client.patch(
        f"{BASE}/{preset['id']}", json={"name": "另一组"}
    )
    assert conflict.status_code == 409

    assert initialized_client.delete(f"{BASE}/{preset['id']}").status_code == 200
    assert initialized_client.delete(f"{BASE}/{preset['id']}").status_code == 404


def test_compare_marks_missing_metrics(initialized_client):
    resp = initialized_client.get("/api/v1/compare?tickers=AAPL,ZZZZ")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    for metric in data["metrics"]:
        assert "missing" in metric
        assert "ZZZZ" in metric["missing"]
    assert any("部分指标缺失" in warning for warning in data["warnings"])
    assert any("ZZZZ" in warning for warning in data["warnings"])
