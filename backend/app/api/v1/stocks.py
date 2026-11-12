"""行情、财务、新闻接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.common import ApiResponse, Meta
from app.schemas.stocks import (
    BarOut,
    FinancialsOut,
    FinancialYearOut,
    HistoryOut,
    NewsItemOut,
    NewsListOut,
    QuoteOut,
)
from app.services.market_service import MarketService

router = APIRouter(prefix="/stocks", tags=["stocks"])

PERIODS = {"1mo", "3mo", "6mo", "1y", "3y", "5y", "max"}
INTERVALS = {"1d", "1wk", "1mo"}


@router.get("/{ticker}/quote")
def get_quote(ticker: str, user: CurrentUser) -> ApiResponse[QuoteOut]:
    quote, meta = MarketService().get_quote(ticker)
    return ApiResponse(data=QuoteOut.model_validate(quote), meta=Meta(**meta))


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
    return ApiResponse(
        data=HistoryOut(
            ticker=ticker.upper(),
            period=period,
            interval=interval,
            bars=[BarOut.model_validate(b) for b in bars],
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
    financials, meta = MarketService().get_financials(ticker, period=period, limit=limit)
    return ApiResponse(
        data=FinancialsOut(
            ticker=financials.ticker,
            currency=financials.currency,
            period=financials.period,
            years=[FinancialYearOut.model_validate(y) for y in financials.years],
        ),
        meta=Meta(**meta),
    )


@router.get("/{ticker}/news")
def get_news(
    ticker: str,
    user: CurrentUser,
    kind: str = Query(default="all", pattern="^(all|news|announcement)$"),
) -> ApiResponse[NewsListOut]:
    items, meta = MarketService().get_news(ticker)
    if kind != "all":
        items = [i for i in items if i.kind == kind]
    return ApiResponse(
        data=NewsListOut(
            ticker=ticker.upper(),
            items=[NewsItemOut.model_validate(i) for i in items],
        ),
        meta=Meta(**meta),
    )
