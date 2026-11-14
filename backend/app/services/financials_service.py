"""财务报表展示层：同比、3 年 CAGR 与缺失项汇总（FR-FIN-03 / FR-FIN-04）。

只做计算与整理，不取数——取数在 MarketService。
"""
from __future__ import annotations

from typing import Any, Optional

from app.analysis.cross_check import cross_check_revenue
from app.providers.models import Financials, FinancialYear
from app.services.market_service import MarketService

# 参与同比/CAGR 的科目，与 FinancialYearOut 的字段同名
FINANCIAL_FIELDS: tuple[str, ...] = (
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "eps",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "total_debt",
    "total_cash",
    "total_equity",
    "shares_outstanding",
)

CAGR_YEARS = 3


def yoy_pct(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """同比：`(本期 − 上期) / |上期|`，单位百分点。

    上期为 0 或缺失时返回 None（不计算，也不填 0）——FR-FIN-04。
    """
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous) * 100


def cagr_pct(latest: Optional[float], base: Optional[float], years: int) -> Optional[float]:
    """复合年均增长率，单位百分点。

    基期非正数时几何增长率没有意义，返回 None，不做符号翻转或估算。
    """
    if latest is None or base is None or years <= 0:
        return None
    if base <= 0 or latest <= 0:
        return None
    return ((latest / base) ** (1.0 / years) - 1.0) * 100


def build_view(financials: Financials) -> dict[str, Any]:
    """把 provider 的财务数据整理成带同比与 CAGR 的展示结构。

    `years` 按财年降序（最新在前）；每一年的 `yoy` 是相对**下一年（更早一期）**的同比。
    最新一期没有上期，同比全为 None。
    """
    years: list[FinancialYear] = sorted(financials.years, key=lambda y: y.year, reverse=True)

    rows: list[dict[str, Any]] = []
    for index, year in enumerate(years):
        previous = years[index + 1] if index + 1 < len(years) else None
        yoy = {
            field: yoy_pct(getattr(year, field), getattr(previous, field)) if previous else None
            for field in FINANCIAL_FIELDS
        }
        rows.append({**year.model_dump(), "yoy": yoy})

    cagr: dict[str, Optional[float]] = {}
    if len(years) > CAGR_YEARS:
        latest, base = years[0], years[CAGR_YEARS]
        cagr = {
            field: cagr_pct(getattr(latest, field), getattr(base, field), CAGR_YEARS)
            for field in FINANCIAL_FIELDS
        }

    missing = sorted(
        {field for year in years for field in FINANCIAL_FIELDS if getattr(year, field) is None}
    )

    return {
        "ticker": financials.ticker,
        "currency": financials.currency,
        "period": financials.period,
        "years": rows,
        "cagr": cagr,
        "cagr_years": CAGR_YEARS,
        "missing_fields": missing,
    }


class FinancialsService:
    """财务报表接口的编排入口。"""

    def __init__(self, market: MarketService | None = None) -> None:
        self.market = market or MarketService()

    def get(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        financials, meta = self.market.get_financials(ticker, period=period, limit=limit)
        view = build_view(financials)

        # A 股交叉校验（FR-DATA-04）：年报营收 vs 新浪 TTM 营收，仅 CN 市场且非缓存时
        cross = None
        if meta.get("source") == "akshare" and financials.years:
            try:
                quote, _ = self.market.get_quote(ticker)
            except Exception:  # noqa: BLE001 - 行情失败不影响财报展示
                quote = None
            if quote is not None:
                cross = cross_check_revenue(
                    financials.years[0].revenue, quote.total_revenue
                )
        if cross is not None:
            view["cross_check"] = cross
        return view, meta
