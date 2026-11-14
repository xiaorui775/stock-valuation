"""个股数据质量接口测试（FR-RESEARCH-05）。"""
from __future__ import annotations

BASE = "/api/v1/stocks"


def test_data_quality_requires_auth(client):
    assert client.get(f"{BASE}/AAPL/data-quality").status_code == 401


def test_data_quality_summarizes_all_sections(initialized_client):
    resp = initialized_client.get(f"{BASE}/AAPL/data-quality")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["ticker"] == "AAPL"
    assert data["checked_at"]
    keys = [section["key"] for section in data["sections"]]
    assert keys == ["quote", "financials", "news", "calendar"]

    quote = data["sections"][0]
    assert quote["source"] == "demo"
    assert quote["stale"] is False
    assert isinstance(quote["missing_fields"], list)
    assert isinstance(data["warnings"], list)
    # 演示数据源不做 A 股交叉校验
    assert data["cross_check"] is None


def test_data_quality_unknown_ticker_returns_404(initialized_client):
    assert initialized_client.get(f"{BASE}/ZZZZ/data-quality").status_code == 404


def test_warnings_cover_stale_missing_and_unavailable():
    from app.services.data_quality_service import DataQualityService

    sections = [
        {
            "key": "quote",
            "label": "行情快照",
            "source": "demo",
            "stale": True,
            "missing_fields": ["beta"],
            "note": None,
        },
        {
            "key": "calendar",
            "label": "财报日历",
            "source": None,
            "stale": False,
            "missing_fields": [],
            "note": "数据源未提供财报日历",
        },
    ]
    warnings = DataQualityService._warnings(
        sections,
        {"conflict": True, "note": "营业收入年报与 TTM 差异较大"},
    )
    assert any("过期缓存" in warning for warning in warnings)
    assert any("beta" in warning for warning in warnings)
    assert any("未提供财报日历" in warning for warning in warnings)
    assert any("差异较大" in warning for warning in warnings)
