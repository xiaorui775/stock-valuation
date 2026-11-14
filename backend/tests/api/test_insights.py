"""财务解读接口测试（§5.6）。"""
from __future__ import annotations

BASE = "/api/v1/stocks"


def test_insights_require_auth(client):
    assert client.get(f"{BASE}/AAPL/insights").status_code == 401


def test_insights_clean_company_has_no_alerts(initialized_client):
    """AAPL 演示数据各规则均可计算但无触发。"""
    resp = initialized_client.get(f"{BASE}/AAPL/insights")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["ticker"] == "AAPL"
    assert data["fiscal_year"] == 2025
    assert data["items"] == []
    assert data["summary"] == "未发现显著异常。"


def test_insights_detects_low_cash_conversion(initialized_client):
    """TSLA 演示数据的自由现金流不足净利润一半。"""
    data = initialized_client.get(f"{BASE}/TSLA/insights").json()["data"]
    alerts = [item for item in data["items"] if item["level"] == "alert"]
    assert alerts, data
    assert alerts[0]["rule"] == "cash_quality"
    assert "自由现金流" in alerts[0]["title"]
    assert alerts[0]["formula"]


def test_insights_items_have_required_fields(initialized_client):
    data = initialized_client.get(f"{BASE}/TSLA/insights").json()["data"]
    for item in data["items"]:
        assert item["rule"] and item["name"] and item["level"] in {"info", "watch", "alert"}
        assert item["title"] and item["detail"] and item["formula"]
        assert item["period"]


def test_insights_reports_uncovered_rules(initialized_client):
    """演示数据齐全时未覆盖项为空；规则无法计算时会列出原因。"""
    data = initialized_client.get(f"{BASE}/AAPL/insights").json()["data"]
    for item in data["uncovered"]:
        assert item["rule"] and item["name"] and item["reason"]


def test_insights_unknown_ticker_returns_404(initialized_client):
    resp = initialized_client.get(f"{BASE}/ZZZZ/insights")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TICKER_NOT_FOUND"
