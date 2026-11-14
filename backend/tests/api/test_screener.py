"""筛选器接口测试（§5.11）。"""
from __future__ import annotations

BASE = "/api/v1/screener"


def _pool(tickers: list[str], **extra) -> dict:
    return {"pool": {"kind": "custom", "tickers": tickers}, **extra}


def _screen(client, body: dict) -> dict:
    resp = client.post(BASE, json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_screener_requires_auth(client):
    assert client.post(BASE, json=_pool(["AAPL", "MSFT"])).status_code == 401


def test_custom_pool_returns_rows(initialized_client):
    data = _screen(initialized_client, _pool(["AAPL", "MSFT", "0700.HK"]))
    assert data["requested"] == 3
    assert data["succeeded"] == 3
    assert data["failed"] == 0
    assert [row["ticker"] for row in data["rows"]] == ["AAPL", "MSFT", "0700.HK"]
    row = data["rows"][0]
    assert row["pe_ttm"] is not None
    assert row["dcf_upside_pct"] is not None
    assert row["revenue_growth"] is not None


def test_filters_narrow_results(initialized_client):
    data = _screen(
        initialized_client,
        _pool(
            ["AAPL", "MSFT", "0700.HK"],
            filters=[{"metric": "pe_ttm", "max": 30}],
        ),
    )
    assert sorted(row["ticker"] for row in data["rows"]) == ["0700.HK", "AAPL"]
    assert all(row["pe_ttm"] <= 30 for row in data["rows"])


def test_multiple_filters_must_all_match(initialized_client):
    data = _screen(
        initialized_client,
        _pool(
            ["AAPL", "MSFT", "0700.HK"],
            filters=[
                {"metric": "pe_ttm", "max": 30},
                {"metric": "dividend_yield", "min": 0.6},
            ],
        ),
    )
    assert [row["ticker"] for row in data["rows"]] == ["0700.HK"]


def test_sorting_by_metric(initialized_client):
    data = _screen(
        initialized_client,
        _pool(["AAPL", "MSFT", "0700.HK"], sort_key="pe_ttm", sort_desc=False),
    )
    values = [row["pe_ttm"] for row in data["rows"]]
    assert values == sorted(values)


def test_failed_tickers_are_excluded_from_rows(initialized_client):
    data = _screen(
        initialized_client,
        _pool(["AAPL", "ZZZZ", "0700.HK"], sort_key="pe_ttm", sort_desc=True),
    )
    assert data["failed"] == 1
    assert [row["ticker"] for row in data["rows"]] == ["AAPL", "0700.HK"]


def test_pagination(initialized_client):
    body = _pool(["AAPL", "MSFT", "0700.HK"], sort_key="pe_ttm", page=2, page_size=1)
    data = _screen(initialized_client, body)
    assert data["total"] == 3
    assert data["page"] == 2
    assert len(data["rows"]) == 1
    assert data["rows"][0]["ticker"] == "AAPL"


def test_market_filter(initialized_client):
    data = _screen(
        initialized_client,
        _pool(["AAPL", "0700.HK", "600519.SS"], market=["CN"]),
    )
    assert [row["ticker"] for row in data["rows"]] == ["600519.SS"]


def test_single_failure_does_not_break_the_result(initialized_client):
    data = _screen(initialized_client, _pool(["AAPL", "ZZZZ"]))
    assert data["succeeded"] == 1
    assert data["failed"] == 1
    assert data["failures"][0]["ticker"] == "ZZZZ"
    assert data["failures"][0]["reason"]


def test_empty_pool_rejected(initialized_client):
    resp = initialized_client.post(BASE, json=_pool([]))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNPROCESSABLE"


def test_pool_over_limit_rejected(initialized_client):
    tickers = [f"T{i}" for i in range(501)]
    resp = initialized_client.post(BASE, json=_pool(tickers))
    assert resp.status_code == 422
    assert "500" in resp.json()["error"]["message"]


def test_filter_without_bounds_rejected(initialized_client):
    resp = initialized_client.post(
        BASE, json=_pool(["AAPL", "MSFT"], filters=[{"metric": "pe_ttm"}])
    )
    assert resp.status_code == 422


def test_filter_with_inverted_bounds_rejected(initialized_client):
    resp = initialized_client.post(
        BASE,
        json=_pool(["AAPL", "MSFT"], filters=[{"metric": "pe_ttm", "min": 30, "max": 10}]),
    )
    assert resp.status_code == 422


def test_watchlist_pool(initialized_client):
    group = initialized_client.get("/api/v1/watchlists").json()["data"]["groups"][0]
    for ticker in ("AAPL", "MSFT"):
        assert (
            initialized_client.post(
                f"/api/v1/watchlists/{group['id']}/items", json={"ticker": ticker}
            ).status_code
            == 201
        )
    data = _screen(
        initialized_client,
        {
            "pool": {"kind": "watchlist", "watchlist_id": group["id"]},
            "filters": [{"metric": "pe_ttm", "max": 30}],
        },
    )
    assert [row["ticker"] for row in data["rows"]] == ["AAPL"]


def test_watchlist_pool_requires_valid_group(initialized_client):
    resp = initialized_client.post(
        BASE, json={"pool": {"kind": "watchlist", "watchlist_id": 9999}}
    )
    assert resp.status_code == 404


def test_estimate_and_elapsed_are_reported(initialized_client):
    data = _screen(initialized_client, _pool(["AAPL", "MSFT"]))
    assert data["estimate_seconds"] >= 1
    assert data["elapsed_ms"] >= 0
    assert "粗略估计" in data["note"]
