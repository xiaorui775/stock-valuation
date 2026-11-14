"""历史估值区间：纯计算与服务行为（FR-VAL-11）。"""
from __future__ import annotations

from datetime import date

import pytest

from app.providers.models import Bar, Financials, FinancialYear, Quote
from app.services.valuation_history_service import (
    MIN_SAMPLES,
    ValuationHistoryService,
    _ratio,
    _shortage,
)
from app.valuation.history import percentile, percentile_rank, percentiles, window_start


class _StubMarket:
    """替身：只返回给定的行情与财报，不做任何网络访问。"""

    def __init__(self, bars, years, quote=None):
        self.bars = bars
        self.financials = Financials(ticker="TEST", currency="USD", years=years)
        self.quote = quote or Quote(ticker="TEST", name="Test", currency="USD", price=100.0)

    def get_quote(self, ticker):
        return self.quote, {"source": "stub"}

    def get_history(self, ticker, period="1y", interval="1d"):
        return self.bars, {"source": "stub"}

    def get_financials(self, ticker, period="annual", limit=5):
        return self.financials, {"source": "stub"}


def _year(year: int, *, eps=2.0, equity=1000.0, shares=100.0, revenue=500.0, fcf=80.0):
    return FinancialYear(
        year=year,
        period_end=date(year, 9, 30),
        revenue=revenue,
        eps=eps,
        total_equity=equity,
        shares_outstanding=shares,
        free_cash_flow=fcf,
    )


def _bars(start: date, count: int, close: float = 20.0):
    """按工作日生成，避免星期几影响断言。"""
    out, day = [], start
    while len(out) < count:
        if day.weekday() < 5:
            out.append(Bar(date=day, close=close))
        day = date.fromordinal(day.toordinal() + 1)
    return out


# ---------- 纯计算 ----------


def test_percentile_linear_interpolation():
    values = [1, 2, 3, 4, 5]
    assert percentile(values, 50) == 3
    assert percentile(values, 0) == 1
    assert percentile(values, 100) == 5
    assert percentile(values, 25) == 2


def test_percentile_single_sample():
    assert percentile([7.0], 90) == 7.0


def test_percentiles_require_min_samples():
    assert percentiles([1.0] * (MIN_SAMPLES - 1)) is None
    stats = percentiles([float(i) for i in range(MIN_SAMPLES)])
    assert stats is not None
    assert set(stats) == {"p10", "p25", "p50", "p75", "p90"}


def test_percentile_rank():
    values = [float(i) for i in range(100)]
    assert percentile_rank(values, -1) == pytest.approx(0)
    assert percentile_rank(values, 1000) == pytest.approx(100)
    assert percentile_rank(values, 50) == pytest.approx(51)
    assert percentile_rank(values, None) is None
    assert percentile_rank([1.0], 1.0) is None  # 样本不足


def test_window_start_handles_leap_day():
    assert window_start(date(2024, 2, 29), 3) == date(2021, 2, 28)
    assert window_start(date(2026, 11, 13), 5) == date(2021, 11, 13)


# ---------- 服务 ----------


def test_history_returns_four_metrics_with_percentiles():
    bars = _bars(date(2021, 1, 4), 900)
    years = [_year(2021), _year(2022), _year(2023), _year(2024), _year(2025)]
    data, _meta = ValuationHistoryService(_StubMarket(bars, years)).get("TEST")

    metrics = {m["key"]: m for m in data["metrics"]}
    assert list(metrics) == ["pe", "pb", "ps", "fcf_yield"]
    pe = metrics["pe"]
    # 收盘 20 / EPS 2 = 10 倍
    assert pe["current"] == pytest.approx(10.0)
    assert pe["stats_5y"]["count"] > MIN_SAMPLES
    assert pe["stats_5y"]["p50"] == pytest.approx(10.0)
    assert pe["percentile_5y"] == pytest.approx(100.0)
    # FCF Yield 以百分点表示：80 / (20 × 100) = 4%
    assert metrics["fcf_yield"]["current"] == pytest.approx(4.0)


def test_history_uses_point_in_time_financials():
    """下一财年报告期之前仍用上一财年的数据，不提前使用新财报。"""
    bars = _bars(date(2023, 1, 2), 180)  # 2023 上半年，尚未到 2023-09-30 报告期
    years = [_year(2022, eps=2.0), _year(2023, eps=4.0)]
    data, _meta = ValuationHistoryService(_StubMarket(bars, years)).get("TEST")
    pe = next(m for m in data["metrics"] if m["key"] == "pe")
    # 全部落在 2023-09-30 之前 → 用 2022 财年 EPS=2 → 20/2=10
    assert pe["current"] == pytest.approx(10.0)


def test_history_drops_days_before_first_fiscal_year():
    bars = _bars(date(2020, 1, 1), 300)  # 早于最早报告期 2024-09-30
    years = [_year(2024), _year(2025)]
    data, _meta = ValuationHistoryService(_StubMarket(bars, years)).get("TEST")
    pe = next(m for m in data["metrics"] if m["key"] == "pe")
    assert pe["current"] is None
    assert pe["stats_5y"] is None


def test_history_reports_missing_eps():
    bars = _bars(date(2021, 1, 4), 400)
    years = [_year(2021, eps=None), _year(2022, eps=None)]
    data, _meta = ValuationHistoryService(_StubMarket(bars, years)).get("TEST")
    pe = next(m for m in data["metrics"] if m["key"] == "pe")
    assert pe["note"] == "年报缺少每股收益（EPS）"
    assert any("P/E" in w for w in data["warnings"])
    # 其他指标不受影响
    ps = next(m for m in data["metrics"] if m["key"] == "ps")
    assert ps["current"] is not None


def test_history_negative_eps_is_explained_not_computed():
    bars = _bars(date(2021, 1, 4), 400)
    years = [_year(2021, eps=-1.0), _year(2022, eps=-2.0)]
    data, _meta = ValuationHistoryService(_StubMarket(bars, years)).get("TEST")
    pe = next(m for m in data["metrics"] if m["key"] == "pe")
    assert "负" in (pe["note"] or "")
    assert pe["current"] is None


def test_history_without_bars_reports_insufficient_data():
    data, _meta = ValuationHistoryService(_StubMarket([], [_year(2024)])).get("TEST")
    assert any("缺少历史行情" in w for w in data["warnings"])
    assert all(m["current"] is None for m in data["metrics"])


def test_history_without_financials_reports_insufficient_data():
    bars = _bars(date(2021, 1, 4), 400)
    data, _meta = ValuationHistoryService(_StubMarket(bars, [])).get("TEST")
    assert any("财务" in w for w in data["warnings"])
    assert all(m["stats_5y"] is None for m in data["metrics"])
    assert data["windows"]["3y"] < data["as_of"].isoformat()


def test_ratio_guards():
    from app.services.valuation_history_service import _Facts

    facts = _Facts(eps=0.0, book_value_per_share=-1.0, revenue=0.0, free_cash_flow=1.0, shares=0.0)
    assert _ratio("pe", 10, facts) is None
    assert _ratio("pb", 10, facts) is None
    assert _ratio("ps", 10, facts) is None
    assert _ratio("fcf_yield", 10, facts) is None
    assert _ratio("unknown", 10, facts) is None


def test_shortage_messages():
    assert _shortage("pb", [_year(2024, equity=None)]) == "年报缺少股东权益"
    assert _shortage("ps", [_year(2024, revenue=None)]) == "年报缺少营业收入"
    assert _shortage("fcf_yield", [_year(2024, fcf=None)]) == "年报缺少自由现金流"
    assert _shortage("pe", [_year(2024)]) is None
