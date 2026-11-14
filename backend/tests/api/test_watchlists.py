"""自选股接口测试（FR-WATCH-01 / 02）。"""
from __future__ import annotations

BASE = "/api/v1/watchlists"


def _default_group(client) -> dict:
    return client.get(BASE).json()["data"]["groups"][0]


def test_watchlists_require_auth(client):
    assert client.get(BASE).status_code == 401


def test_first_list_creates_default_group(initialized_client):
    data = initialized_client.get(BASE).json()["data"]
    assert len(data["groups"]) == 1
    assert data["groups"][0]["name"] == "我的自选"
    assert data["groups"][0]["items"] == []


def test_create_rename_and_delete_group(initialized_client):
    created = initialized_client.post(BASE, json={"name": "观察池"})
    assert created.status_code == 201, created.text
    group = created.json()["data"]
    assert group["name"] == "观察池"

    renamed = initialized_client.patch(f"{BASE}/{group['id']}", json={"name": "核心持仓"})
    assert renamed.status_code == 200
    assert renamed.json()["data"]["name"] == "核心持仓"

    deleted = initialized_client.delete(f"{BASE}/{group['id']}")
    assert deleted.status_code == 200
    names = [g["name"] for g in initialized_client.get(BASE).json()["data"]["groups"]]
    assert "核心持仓" not in names


def test_duplicate_group_name_conflicts(initialized_client):
    initialized_client.get(BASE)  # 创建默认分组
    resp = initialized_client.post(BASE, json={"name": "我的自选"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_add_item_and_duplicate_conflict(initialized_client):
    group = _default_group(initialized_client)
    resp = initialized_client.post(
        f"{BASE}/{group['id']}/items", json={"ticker": "aapl"}
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()["data"]
    assert item["ticker"] == "AAPL"
    assert item["name"] == "Apple Inc."
    assert item["market"] == "US"

    again = initialized_client.post(
        f"{BASE}/{group['id']}/items", json={"ticker": "AAPL"}
    )
    assert again.status_code == 409


def test_add_invalid_ticker_returns_404(initialized_client):
    group = _default_group(initialized_client)
    resp = initialized_client.post(
        f"{BASE}/{group['id']}/items", json={"ticker": "ZZZZ"}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TICKER_NOT_FOUND"


def test_batch_add_reports_failures(initialized_client):
    group = _default_group(initialized_client)
    resp = initialized_client.post(
        f"{BASE}/{group['id']}/items/batch",
        json={"tickers": ["AAPL", "0700.HK", "ZZZZ", "AAPL"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert [item["ticker"] for item in data["added"]] == ["AAPL", "0700.HK"]
    failed = {item["ticker"] for item in data["failed"]}
    assert failed == {"ZZZZ", "AAPL"}

    listed = initialized_client.get(BASE).json()["data"]["groups"][0]["items"]
    assert [item["ticker"] for item in listed] == ["AAPL", "0700.HK"]


def test_remove_item(initialized_client):
    group = _default_group(initialized_client)
    item = initialized_client.post(
        f"{BASE}/{group['id']}/items", json={"ticker": "AAPL"}
    ).json()["data"]

    resp = initialized_client.delete(f"{BASE}/{group['id']}/items/{item['id']}")
    assert resp.status_code == 200
    assert initialized_client.get(BASE).json()["data"]["groups"][0]["items"] == []

    again = initialized_client.delete(f"{BASE}/{group['id']}/items/{item['id']}")
    assert again.status_code == 404


def test_reorder_items(initialized_client):
    group = _default_group(initialized_client)
    ids = {}
    for ticker in ("AAPL", "MSFT", "NVDA"):
        ids[ticker] = initialized_client.post(
            f"{BASE}/{group['id']}/items", json={"ticker": ticker}
        ).json()["data"]["id"]

    resp = initialized_client.patch(
        f"{BASE}/{group['id']}/items/order",
        json={"item_ids": [ids["NVDA"], ids["AAPL"], ids["MSFT"]]},
    )
    assert resp.status_code == 200
    assert [item["ticker"] for item in resp.json()["data"]] == ["NVDA", "AAPL", "MSFT"]


def test_reorder_groups(initialized_client):
    first = _default_group(initialized_client)
    second = initialized_client.post(BASE, json={"name": "观察池"}).json()["data"]

    resp = initialized_client.patch(
        f"{BASE}/order", json={"group_ids": [second["id"], first["id"]]}
    )
    assert resp.status_code == 200
    assert [g["id"] for g in resp.json()["data"]["groups"]] == [second["id"], first["id"]]


def test_group_isolation_between_users(initialized_client, db):
    """别人的分组不可见、不可改。"""
    from app.models.user import User

    other = User(
        email="other@example.com",
        display_name="其他人",
        password_hash="x",
        base_currency="CNY",
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    from app.services.watchlist_service import WatchlistService

    group = WatchlistService(db).create_group(other.id, "他人分组")

    resp = initialized_client.patch(f"{BASE}/{group['id']}", json={"name": "改名"})
    assert resp.status_code == 404
    assert initialized_client.delete(f"{BASE}/{group['id']}").status_code == 404


def test_group_quotes_returns_market_and_valuation_columns(initialized_client):
    group = _default_group(initialized_client)
    for ticker in ("AAPL", "0700.HK"):
        initialized_client.post(f"{BASE}/{group['id']}/items", json={"ticker": ticker})

    resp = initialized_client.get(f"{BASE}/{group['id']}/quotes")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["group_id"] == group["id"]
    assert data["refreshed_at"]

    rows = {row["ticker"]: row for row in data["items"]}
    assert set(rows) == {"AAPL", "0700.HK"}
    aapl = rows["AAPL"]
    assert aapl["price"] == 182.5
    assert aapl["change_pct"] is not None
    assert aapl["market_cap"] is not None
    assert aapl["pe_ttm"] is not None
    assert aapl["forward_pe"] is not None
    assert aapl["dividend_yield"] is not None
    assert aapl["fcf_yield"] is not None
    assert aapl["dcf_upside_pct"] is not None
    assert aapl["error"] is None
    assert aapl["stale"] is False


def test_group_quotes_requires_ownership(initialized_client, db):
    from app.models.user import User
    from app.services.watchlist_service import WatchlistService

    other = User(
        email="third@example.com",
        display_name="第三者",
        password_hash="x",
        base_currency="CNY",
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    group = WatchlistService(db).create_group(other.id, "他人分组")

    resp = initialized_client.get(f"{BASE}/{group['id']}/quotes")
    assert resp.status_code == 404


def test_quote_row_failure_is_isolated(db):
    """单只标的取数失败时该行带 error，不影响其他行（FR-WATCH-05）。"""
    from app.core.errors import TickerNotFound
    from app.models.watchlist import WatchlistGroup, WatchlistItem
    from app.services.watchlist_service import WatchlistService

    class BrokenMarket:
        def get_quote(self, ticker):
            raise TickerNotFound(ticker)

        def get_financials(self, ticker):
            raise TickerNotFound(ticker)

    group = WatchlistGroup(user_id=1, name="G", sort_order=0)
    db.add(group)
    db.commit()
    db.refresh(group)
    item = WatchlistItem(
        group_id=group.id, ticker="ZZZZ", name="ZZZZ", market="US", sort_order=0
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    row = WatchlistService(db, market=BrokenMarket())._quote_row(item)
    assert row["ticker"] == "ZZZZ"
    assert row["error"]
    assert row["price"] is None
    assert row["stale"] is False
