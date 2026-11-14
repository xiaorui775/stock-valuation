"""Provider 层测试：字段映射与市场识别。"""
from __future__ import annotations

import pytest

from app.providers.base import detect_market
from app.providers.demo_provider import DemoProvider
from app.providers.models import Market
from app.providers.yfinance_provider import _collect_missing, normalize_yield


def test_detect_market():
    assert detect_market("600519.SS") == Market.CN
    assert detect_market("000001.SZ") == Market.CN
    assert detect_market("830799.BJ") == Market.CN
    assert detect_market("0700.HK") == Market.HK
    assert detect_market("AAPL") == Market.US
    assert detect_market("aapl") == Market.US


def test_normalize_yield_fraction_to_percent():
    assert normalize_yield(0.0052) == 0.52
    assert normalize_yield(0.52) == 0.52
    assert normalize_yield(None) is None


def test_collect_missing_lists_absent_fields():
    quote = DemoProvider().get_quote("AAPL")
    missing = _collect_missing(quote)
    assert "price" not in missing  # 演示数据有价格
    assert isinstance(missing, list)


def test_demo_quote_shape():
    quote = DemoProvider().get_quote("aapl")
    assert quote.ticker == "AAPL"
    assert quote.price == 182.50
    assert quote.change is not None
    assert quote.dividend_yield == 0.52  # 演示数据 dividendYield=0.0052 → 0.52%
    assert quote.provider == "demo"


def test_demo_history_last_close_matches_quote():
    demo = DemoProvider()
    bars = demo.get_history("AAPL", period="1y")
    assert len(bars) > 200
    assert bars[-1].close == demo.get_quote("AAPL").price


def test_demo_financials_has_fcf():
    financials = DemoProvider().get_financials("AAPL")
    year = financials.years[0]
    assert len(financials.years) == 5
    assert year.free_cash_flow == 112_000_000_000
    # 资本开支以负数表示，自由现金流 = 经营现金流 + 资本开支
    assert year.capex < 0
    assert year.operating_cash_flow + year.capex == pytest.approx(year.free_cash_flow)


def test_demo_scale_is_plausible():
    """演示数据的量级应与真实公司同阶，避免市值/营收出现天文数字。"""
    demo = DemoProvider()
    for ticker in ("AAPL", "0700.HK", "600519.SS", "000001.SZ"):
        quote = demo.get_quote(ticker)
        financials = demo.get_financials(ticker).years[0]
        assert quote.market_cap == pytest.approx(quote.price * quote.shares_outstanding)
        assert quote.shares_outstanding == financials.shares_outstanding
        # 市值 / 营收 落在合理区间（0.5x – 60x）
        ratio = quote.market_cap / financials.revenue
        assert 0.5 < ratio < 60, (ticker, ratio)


def test_demo_news_kinds():
    items = DemoProvider().get_news("AAPL")
    kinds = {i.kind for i in items}
    assert kinds == {"news", "announcement"}
