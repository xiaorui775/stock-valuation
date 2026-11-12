"""演示模式数据源：内置样本，不访问网络。

用于 STOCKVAL_DEMO=1 时的离线演示与前端联调。
"""
from __future__ import annotations

import math
import random
from datetime import UTC, date, datetime, timedelta
from typing import ClassVar

from app.providers.base import detect_market
from app.providers.models import (
    Bar,
    CalendarInfo,
    Financials,
    FinancialYear,
    Instrument,
    Market,
    NewsItem,
    Quote,
)

_DEMO_INFO = {
    "symbol": "DEMO",
    "shortName": "示例科技（演示数据）",
    "currency": "USD",
    "currentPrice": 182.50,
    "previousClose": 179.20,
    "regularMarketDayHigh": 185.10,
    "regularMarketDayLow": 178.40,
    "open": 180.10,
    "marketCap": 2_850_000_000_000,
    "trailingPE": 28.4,
    "forwardPE": 24.1,
    "trailingEps": 6.43,
    "dividendYield": 0.0052,
    "beta": 1.18,
    "fiftyTwoWeekHigh": 199.62,
    "fiftyTwoWeekLow": 124.17,
    "regularMarketVolume": 48_230_000,
    "sharesOutstanding": 15_615_000_000,
    "priceToBook": 45.2,
    "priceToSalesTrailing12Months": 7.4,
    "enterpriseToEbitda": 21.3,
    "pegRatio": 1.9,
    "totalDebt": 108_000_000_000,
    "totalCash": 61_500_000_000,
    "totalRevenue": 385_000_000_000,
    "ebitda": 132_000_000_000,
    "bookValue": 4.04,
}

_DEMO_FINANCIALS = [
    {"year": 2025, "revenue": 416_000_000_000, "gross_profit": 190_000_000_000,
     "operating_income": 128_000_000_000, "net_income": 105_000_000_000,
     "free_cash_flow": 112_000_000_000},
    {"year": 2024, "revenue": 391_000_000_000, "gross_profit": 177_000_000_000,
     "operating_income": 119_000_000_000, "net_income": 97_000_000_000,
     "free_cash_flow": 105_000_000_000},
    {"year": 2023, "revenue": 383_000_000_000, "gross_profit": 169_000_000_000,
     "operating_income": 114_000_000_000, "net_income": 99_800_000_000,
     "free_cash_flow": 99_500_000_000},
    {"year": 2022, "revenue": 365_000_000_000, "gross_profit": 156_000_000_000,
     "operating_income": 105_000_000_000, "net_income": 90_000_000_000,
     "free_cash_flow": 92_000_000_000},
]


class DemoProvider:
    """离线样本数据源。"""

    name: ClassVar[str] = "demo"
    markets: ClassVar[set[str]] = {Market.US.value, Market.HK.value, Market.CN.value}

    def search(self, query: str) -> list[Instrument]:
        q = (query or "").strip()
        if not q:
            return []
        return [
            Instrument(
                ticker=q.upper(),
                name=f"{q.upper()}（演示数据）",
                market=detect_market(q),
                currency="USD",
                provider=self.name,
            )
        ]

    def get_quote(self, ticker: str) -> Quote:
        info = dict(_DEMO_INFO)
        symbol = (ticker or "DEMO").upper()
        price = info["currentPrice"]
        prev = info["previousClose"]
        quote = Quote(
            ticker=symbol,
            name=info["shortName"],
            currency=info["currency"],
            market=detect_market(symbol),
            price=price,
            previous_close=prev,
            change=price - prev,
            change_pct=(price - prev) / prev * 100,
            day_high=info["regularMarketDayHigh"],
            day_low=info["regularMarketDayLow"],
            open_price=info["open"],
            market_cap=info["marketCap"],
            pe_ttm=info["trailingPE"],
            forward_pe=info["forwardPE"],
            eps_ttm=info["trailingEps"],
            dividend_yield=info["dividendYield"] * 100,
            beta=info["beta"],
            week52_high=info["fiftyTwoWeekHigh"],
            week52_low=info["fiftyTwoWeekLow"],
            volume=info["regularMarketVolume"],
            shares_outstanding=info["sharesOutstanding"],
            price_to_book=info["priceToBook"],
            price_to_sales=info["priceToSalesTrailing12Months"],
            ev_ebitda=info["enterpriseToEbitda"],
            peg=info["pegRatio"],
            total_debt=info["totalDebt"],
            total_cash=info["totalCash"],
            total_revenue=info["totalRevenue"],
            ebitda=info["ebitda"],
            book_value_per_share=info["bookValue"],
            as_of=datetime.now(UTC),
            provider=self.name,
        )
        return quote

    def get_history(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> list[Bar]:
        random.seed(42)
        points: list[Bar] = []
        price = 130.0
        periods = {"1mo": 22, "3mo": 66, "6mo": 130, "1y": 252, "3y": 756, "5y": 1260}
        count = periods.get(period, 252)
        if interval == "1wk":
            count = count // 5
        elif interval == "1mo":
            count = count // 21
        today = date.today()
        days = count
        dates = [today - timedelta(days=i) for i in range(days, 0, -1)]
        for i, d in enumerate(dates):
            price *= 1 + 0.0016 + random.gauss(0, 0.011) + 0.02 * math.sin(i / 23.0) / 100
            points.append(
                Bar(
                    date=d,
                    open=round(price * 0.998, 2),
                    high=round(price * 1.006, 2),
                    low=round(price * 0.994, 2),
                    close=round(price, 2),
                    volume=30_000_000 + int(random.random() * 30_000_000),
                )
            )
        # 让最后一天收盘与演示报价一致
        points[-1].close = _DEMO_INFO["currentPrice"]
        return points

    def get_financials(self, ticker: str, period: str = "annual", limit: int = 5) -> Financials:
        years = [
            FinancialYear(
                year=item["year"],
                period_end=date(item["year"], 12, 31),
                revenue=item["revenue"],
                gross_profit=item["gross_profit"],
                operating_income=item["operating_income"],
                net_income=item["net_income"],
                eps=round(item["net_income"] / _DEMO_INFO["sharesOutstanding"], 4),
                operating_cash_flow=item["free_cash_flow"] + 12_000_000_000,
                capex=-12_000_000_000,
                free_cash_flow=item["free_cash_flow"],
                total_debt=_DEMO_INFO["totalDebt"],
                total_cash=_DEMO_INFO["totalCash"],
                total_equity=_DEMO_INFO["sharesOutstanding"] * _DEMO_INFO["bookValue"],
                shares_outstanding=_DEMO_INFO["sharesOutstanding"],
            )
            for item in _DEMO_FINANCIALS[:limit]
        ]
        return Financials(
            ticker=(ticker or "DEMO").upper(),
            currency="USD",
            period=period,
            years=years,
            provider=self.name,
        )

    def get_news(self, ticker: str) -> list[NewsItem]:
        now = datetime.now(UTC)
        return [
            NewsItem(
                title=f"{ticker.upper()} 发布季度业绩，收入同比增长 8%（演示数据）",
                url=None,
                source="演示数据源",
                kind="news",
                published_at=now - timedelta(hours=5),
            ),
            NewsItem(
                title=f"{ticker.upper()} 宣布回购计划，金额 50 亿美元（演示数据）",
                url=None,
                source="演示数据源",
                kind="announcement",
                published_at=now - timedelta(days=1, hours=3),
            ),
        ]

    def get_calendar(self, ticker: str) -> CalendarInfo | None:
        return CalendarInfo(earnings_date=date.today() + timedelta(days=21))
