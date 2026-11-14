"""行情、财务、新闻接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.analysis.indicators import compute_all
from app.api.deps import CurrentUser
from app.core.tickers import normalize_ticker
from app.providers.base import detect_market
from app.schemas.common import ApiResponse, Meta
from app.schemas.insights import InsightsOut
from app.schemas.stocks import (
    BarOut,
    CalendarOut,
    DataQualityOut,
    FinancialsOut,
    HistoryOut,
    IndicatorsOut,
    NewsItemOut,
    NewsListOut,
    OverviewOut,
    QuoteOut,
)
from app.services.data_quality_service import DataQualityService
from app.services.financials_service import FinancialsService
from app.services.insight_service import InsightService
from app.services.market_calendar import days_until
from app.services.market_service import MarketService
from app.services.news_service import dedupe_news
from app.services.overview_service import OverviewService

router = APIRouter(prefix="/stocks", tags=["stocks"])

PERIODS = {"1mo", "3mo", "6mo", "1y", "3y", "5y", "max"}
INTERVALS = {"1d", "1wk", "1mo"}

# yfinance 使用 auto_adjust=True：历史价格按拆股/分红调整且以最新价为锚，即前复权。
# 演示数据源同口径，因此这里统一声明（FR-CHART-05 要求在图表下方提示复权方式）。
ADJUSTMENT = "前复权"


@router.get("/{ticker}/overview")
def get_overview(ticker: str, user: CurrentUser) -> ApiResponse[OverviewOut]:
    """个股概览：报价头 + 交易时段 + 52 周位置 + 估值结论。"""
    data, meta = OverviewService().build(ticker)
    return ApiResponse(data=OverviewOut.model_validate(data), meta=Meta(**meta))


@router.get("/{ticker}/insights")
def get_insights(ticker: str, user: CurrentUser) -> ApiResponse[InsightsOut]:
    """规则化财务解读：事实列表 + 未覆盖项（§5.6）。"""
    data, meta = InsightService().get(ticker)
    return ApiResponse(data=InsightsOut.model_validate(data), meta=Meta(**meta))


@router.get("/{ticker}/quote")
def get_quote(ticker: str, user: CurrentUser) -> ApiResponse[QuoteOut]:
    quote, meta = MarketService().get_quote(ticker)
    return ApiResponse(data=QuoteOut.model_validate(quote), meta=Meta(**meta))


@router.get("/{ticker}/calendar")
def get_calendar(ticker: str, user: CurrentUser) -> ApiResponse[CalendarOut]:
    """下一次财报日与分红/除息日；仅信息展示，不做提醒或推送（FR-RESEARCH-04）。"""
    info, meta = MarketService().get_calendar(ticker)
    symbol = normalize_ticker(ticker)
    days = None
    note = None
    if info is None:
        note = "数据源未提供财报日历"
    elif info.earnings_date is None:
        note = "数据源未提供下一次财报日"
    else:
        days = days_until(info.earnings_date, detect_market(symbol))
        if days is None:
            note = "数据源提供的财报日已过，未提供下一次日期"
    payload = {
        "ticker": symbol,
        "earnings_date": info.earnings_date if info else None,
        "dividend_date": info.dividend_date if info else None,
        "ex_dividend_date": info.ex_dividend_date if info else None,
        "days_until_earnings": days,
        "note": note,
    }
    return ApiResponse(data=CalendarOut.model_validate(payload), meta=Meta(**meta))


@router.get("/{ticker}/data-quality")
def get_data_quality(ticker: str, user: CurrentUser) -> ApiResponse[DataQualityOut]:
    """个股数据质量汇总：来源、缓存/stale、缺失字段与交叉校验差异（FR-RESEARCH-05）。"""
    data = DataQualityService().build(ticker)
    return ApiResponse(
        data=DataQualityOut.model_validate(data),
        meta=Meta(source="local"),
    )


@router.get("/{ticker}/history")
def get_history(
    ticker: str,
    user: CurrentUser,
    period: str = Query(default="1y"),
    interval: str = Query(default="1d"),
) -> ApiResponse[HistoryOut]:
    period = period.lower()
    interval = interval.lower()
    if period not in PERIODS:
        period = "1y"
    if interval not in INTERVALS:
        interval = "1d"
    bars, meta = MarketService().get_history(ticker, period=period, interval=interval)
    closes = [bar.close for bar in bars]
    indicators = compute_all(closes)
    return ApiResponse(
        data=HistoryOut(
            ticker=ticker.upper(),
            period=period,
            interval=interval,
            adjustment=ADJUSTMENT,
            start_date=bars[0].date if bars else None,
            end_date=bars[-1].date if bars else None,
            count=len(bars),
            bars=[BarOut.model_validate(b) for b in bars],
            indicators=IndicatorsOut.model_validate(indicators),
        ),
        meta=Meta(**meta),
    )


@router.get("/{ticker}/financials")
def get_financials(
    ticker: str,
    user: CurrentUser,
    period: str = Query(default="annual", pattern="^(annual|quarterly)$"),
    limit: int = Query(default=5, ge=1, le=20),
) -> ApiResponse[FinancialsOut]:
    financials, meta = FinancialsService().get(ticker, period=period, limit=limit)
    return ApiResponse(data=FinancialsOut.model_validate(financials), meta=Meta(**meta))


@router.get("/{ticker}/news")
def get_news(
    ticker: str,
    user: CurrentUser,
    kind: str = Query(default="all", pattern="^(all|news|announcement)$"),
) -> ApiResponse[NewsListOut]:
    items, meta = MarketService().get_news(ticker)
    items = dedupe_news(items)
    if kind != "all":
        items = [i for i in items if i.kind == kind]
    # FR-NEWS-02：分页 20 条；完整列表由前端分页取回
    items = items[:20]
    return ApiResponse(
        data=NewsListOut(
            ticker=ticker.upper(),
            items=[NewsItemOut.model_validate(i) for i in items],
        ),
        meta=Meta(**meta),
    )
