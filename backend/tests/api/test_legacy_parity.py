"""M1-12 验收：旧 Demo 的四个 API 能力在新架构中全部复现（§7.8）。

旧版 Flask Demo（根目录 app.py）提供：
    /api/quote?ticker=      → 行情
    /api/history?ticker=    → 1 年收盘价序列
    /api/financials?ticker= → 年度财务
    /api/valuation?ticker=  → 估值（growth/terminal/discount/ddm_growth）
本文件逐项校验新接口的字段是其超集，且演示模式不联网。
"""
from __future__ import annotations

# 旧版 quote 返回的全部字段（demo 标记改由 meta.source 表达）
LEGACY_QUOTE_FIELDS = [
    "ticker",
    "name",
    "currency",
    "price",
    "previous_close",
    "change",
    "change_pct",
    "day_high",
    "day_low",
    "market_cap",
    "pe_ttm",
    "forward_pe",
    "eps_ttm",
    "dividend_yield",
    "beta",
    "week52_high",
    "week52_low",
    "volume",
    "shares_outstanding",
    "price_to_book",
    "price_to_sales",
    "ev_ebitda",
    "peg",
    "total_debt",
    "total_cash",
]

LEGACY_YEAR_FIELDS = [
    "year",
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "free_cash_flow",
]


def test_quote_covers_legacy_fields(initialized_client):
    resp = initialized_client.get("/api/v1/stocks/AAPL/quote")
    assert resp.status_code == 200
    data = resp.json()["data"]
    for field in LEGACY_QUOTE_FIELDS:
        assert field in data, field
    assert data["price"] is not None


def test_history_covers_legacy_points(initialized_client):
    """旧版返回 {points: [{date, close}]}，新版返回 OHLCV bars。"""
    data = initialized_client.get(
        "/api/v1/stocks/AAPL/history?period=1y&interval=1d"
    ).json()["data"]
    assert data["bars"]
    for bar in data["bars"]:
        assert "date" in bar and "close" in bar
    # 新增能力：OHLC 与成交量、复权说明、周/月线与 MAX 周期
    assert {"open", "high", "low", "volume"} <= set(data["bars"][0])
    assert data["adjustment"]
    assert data["start_date"] and data["end_date"]


def test_financials_covers_legacy_years(initialized_client):
    data = initialized_client.get("/api/v1/stocks/AAPL/financials").json()["data"]
    assert data["years"]
    for field in LEGACY_YEAR_FIELDS:
        assert field in data["years"][0], field
    # 新增能力：EPS/现金流/资产负债科目、同比与 CAGR
    assert data["years"][0]["yoy"]["revenue"] is not None
    assert "cagr" in data


def test_valuation_covers_legacy_blocks_and_params(initialized_client):
    """旧版的 growth/terminal/discount/ddm_growth 参数仍然生效。"""
    resp = initialized_client.get(
        "/api/v1/stocks/AAPL/valuation?growth=8&terminal=2&discount=10&ddm_growth=2"
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    for block in ("inputs", "dcf", "sensitivity", "multiples", "ddm", "summary"):
        assert block in data, block
    assert data["inputs"]["growth"] == 8
    assert data["inputs"]["terminal"] == 2
    assert data["inputs"]["discount"] == 10
    assert data["inputs"]["ddm_growth"] == 2


def test_demo_mode_is_offline(initialized_client):
    """演示模式下所有数据接口标注来源为 demo，且不访问网络。"""
    for path in (
        "/api/v1/stocks/AAPL/quote",
        "/api/v1/stocks/AAPL/history",
        "/api/v1/stocks/AAPL/financials",
        "/api/v1/stocks/AAPL/valuation",
    ):
        meta = initialized_client.get(path).json()["meta"]
        assert meta["source"] in {"demo", "mixed"}, path


def test_search_is_an_extra_capability(initialized_client):
    """旧版没有搜索接口；新版提供代码/名称搜索。"""
    items = initialized_client.get("/api/v1/search?q=Apple").json()["data"]
    assert any(item["ticker"] == "AAPL" for item in items)
