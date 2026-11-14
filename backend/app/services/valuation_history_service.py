"""历史估值区间：历史价格 × 对应财年财务（FR-VAL-11）。

口径说明：每个交易日的估值倍数用「该日之前最近一个已完成财年」的财报数据计算，
不引入未来数据；财报缺失的日期直接不参与统计，而不是用最新财报回填。
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from app.core.errors import AppError
from app.services.market_service import MarketService
from app.valuation.history import MIN_SAMPLES, percentile_rank, percentiles, window_start

WINDOWS = (3, 5)
HISTORY_PERIOD = "5y"


@dataclass(frozen=True)
class _Facts:
    """某财年可用于估值倍数计算的每股/规模数据。"""

    eps: Optional[float]
    book_value_per_share: Optional[float]
    revenue: Optional[float]
    free_cash_flow: Optional[float]
    shares: Optional[float]


METRICS: tuple[tuple[str, str, str], ...] = (
    ("pe", "P/E（市盈率）", "倍"),
    ("pb", "P/B（市净率）", "倍"),
    ("ps", "P/S（市销率）", "倍"),
    ("fcf_yield", "FCF Yield", "%"),
)


def _ratio(metric: str, close: float, facts: _Facts) -> Optional[float]:
    """单日倍数；分母缺失或非正时返回 None（倍数没有意义）。"""
    if metric == "pe":
        return close / facts.eps if facts.eps and facts.eps > 0 else None
    if metric == "pb":
        bvps = facts.book_value_per_share
        return close / bvps if bvps and bvps > 0 else None
    if metric == "ps":
        if not facts.revenue or facts.revenue <= 0 or not facts.shares:
            return None
        return close * facts.shares / facts.revenue
    if metric == "fcf_yield":
        if facts.free_cash_flow is None or not facts.shares or close <= 0:
            return None
        return facts.free_cash_flow / (close * facts.shares) * 100
    return None


def _facts(year) -> _Facts:
    shares = year.shares_outstanding
    equity = year.total_equity
    bvps = equity / shares if equity is not None and shares and shares > 0 else None
    return _Facts(
        eps=year.eps,
        book_value_per_share=bvps,
        revenue=year.revenue,
        free_cash_flow=year.free_cash_flow,
        shares=shares,
    )


def _shortage(metric: str, years: list) -> Optional[str]:
    """该指标数据不足时给出缺什么的说明（PRD 要求「说明缺什么」）。"""
    if metric == "pe":
        if all(year.eps is None for year in years):
            return "年报缺少每股收益（EPS）"
        if all((year.eps or 0) <= 0 for year in years):
            return "各财年每股收益均为负，市盈率没有意义"
    elif metric == "pb":
        if all(year.total_equity is None for year in years):
            return "年报缺少股东权益"
        if all(year.shares_outstanding is None for year in years):
            return "年报缺少总股本"
    elif metric == "ps":
        if all(year.revenue is None for year in years):
            return "年报缺少营业收入"
        if all(year.shares_outstanding is None for year in years):
            return "年报缺少总股本"
    elif metric == "fcf_yield" and all(year.free_cash_flow is None for year in years):
        return "年报缺少自由现金流"
    return None


class ValuationHistoryService:
    def __init__(self, market: MarketService | None = None) -> None:
        self.market = market or MarketService()

    def get(self, ticker: str) -> tuple[dict[str, Any], dict[str, Any]]:
        quote, meta = self.market.get_quote(ticker)
        warnings: list[str] = []

        try:
            bars, _ = self.market.get_history(quote.ticker, period=HISTORY_PERIOD, interval="1d")
        except AppError:  # 行情失败时整体按数据不足处理
            bars = []
        try:
            financials, _ = self.market.get_financials(quote.ticker, period="annual", limit=5)
        except AppError:  # 财报失败时整体按数据不足处理
            financials = None

        years = sorted(
            (y for y in (financials.years if financials else []) if y.period_end),
            key=lambda y: y.period_end,
        )
        bars = sorted(bars, key=lambda bar: bar.date)

        if not bars:
            warnings.append("缺少历史行情，无法计算历史估值区间")
        if not years:
            warnings.append("缺少年度财务数据（含报告期），无法匹配历史价格")

        metrics = [
            self._metric(key, label, unit, bars, years, warnings)
            for key, label, unit in METRICS
        ]

        as_of = bars[-1].date if bars else date.today()
        data = {
            "ticker": quote.ticker,
            "currency": quote.currency,
            "as_of": as_of,
            "windows": {
                f"{n}y": window_start(as_of, n).isoformat() for n in WINDOWS
            },
            "sample_hint": (
                f"每个交易日使用该日之前最近一个已完成财年；亏损日（EPS、每股净资产 ≤ 0）"
                f"不计入对应指标的样本；样本不足 {MIN_SAMPLES} 个时不给分位数"
            ),
            "metrics": metrics,
            "warnings": warnings,
        }
        return data, meta

    def _metric(
        self,
        key: str,
        label: str,
        unit: str,
        bars: list,
        years: list,
        warnings: list[str],
    ) -> dict[str, Any]:
        series = self._series(key, bars, years)
        current = series[-1][1] if series else None
        entry: dict[str, Any] = {
            "key": key,
            "label": label,
            "unit": unit,
            "current": current,
            "percentile_3y": None,
            "percentile_5y": None,
            "stats_3y": None,
            "stats_5y": None,
            "note": None,
        }

        shortage = _shortage(key, years)
        if shortage:
            entry["note"] = shortage
            warnings.append(f"{label}：{shortage}")
            return entry
        if not bars:
            entry["note"] = "缺少历史行情"
            return entry

        as_of = bars[-1].date
        for window in WINDOWS:
            start = window_start(as_of, window)
            values = [value for day, value in series if day >= start]
            stats = percentiles(values)
            if stats is None:
                continue
            stats["count"] = len(values)
            entry[f"stats_{window}y"] = stats
            entry[f"percentile_{window}y"] = percentile_rank(values, current)

        if series and entry["stats_5y"] is None:
            entry["note"] = f"有效样本 {len(series)} 个，少于 {MIN_SAMPLES} 个，不给分位数"
        return entry

    def _series(self, metric: str, bars: list, years: list) -> list[tuple[date, float]]:
        """`[(交易日, 倍数)]`，只包含财报可用之后的日子。"""
        if not years or not bars:
            return []
        period_ends = [y.period_end for y in years]
        facts = [_facts(y) for y in years]
        series: list[tuple[date, float]] = []
        for bar in bars:
            index = bisect_right(period_ends, bar.date) - 1
            if index < 0:
                continue
            value = _ratio(metric, bar.close, facts[index])
            if value is not None:
                series.append((bar.date, value))
        return series
