"""演示模式数据源：内置样本，不访问网络。

用于 STOCKVAL_DEMO=1 时的离线演示与前端联调。
"""
from __future__ import annotations

import math
import random
import zlib
from datetime import UTC, date, datetime, timedelta
from typing import Any, ClassVar

from app.core.tickers import parse_ticker
from app.providers.base import TickerNotFound, detect_market
from app.providers.models import (
    Bar,
    CalendarInfo,
    Financials,
    FinancialYear,
    Instrument,
    InstrumentKind,
    Market,
    NewsItem,
    Quote,
)

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
    {"year": 2021, "revenue": 348_000_000_000, "gross_profit": 148_000_000_000,
     "operating_income": 100_000_000_000, "net_income": 86_000_000_000,
     "free_cash_flow": 88_000_000_000},
]


_DEMO_INSTRUMENTS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "market": Market.US, "exchange": "NASDAQ",
     "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "market": Market.US, "exchange": "NASDAQ",
     "currency": "USD"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "market": Market.US, "exchange": "NASDAQ",
     "currency": "USD"},
    {"ticker": "TSLA", "name": "Tesla, Inc.", "market": Market.US, "exchange": "NASDAQ",
     "currency": "USD"},
    {"ticker": "AMZN", "name": "Amazon.com, Inc.", "market": Market.US, "exchange": "NASDAQ",
     "currency": "USD"},
    {"ticker": "0700.HK", "name": "腾讯控股", "market": Market.HK, "exchange": "HKEX",
     "currency": "HKD"},
    {"ticker": "9988.HK", "name": "阿里巴巴-W", "market": Market.HK, "exchange": "HKEX",
     "currency": "HKD"},
    {"ticker": "600519.SS", "name": "贵州茅台", "market": Market.CN, "exchange": "上交所",
     "currency": "CNY"},
    {"ticker": "000001.SZ", "name": "平安银行", "market": Market.CN, "exchange": "深交所",
     "currency": "CNY"},
    {"ticker": "830799.BJ", "name": "艾融软件", "market": Market.CN, "exchange": "北交所",
     "currency": "CNY"},
]


# 每个标的的画像，均按本币计价。演示数据是合成的，但量级与真实公司同阶：
# 市值 = 价格 × 股本，EPS = 净利润 / 股本，P/S = 市值 / 收入 均由这里推导，
# 避免出现「贵州茅台营收 39 万亿元」「总股本 1.47 万亿股」这类失真数字。
#   price / shares     现价与总股本
#   revenue / net      最新财年营业收入、净利润
#   fcf                最新财年自由现金流
#   debt / cash        总债务、现金及等价物
#   book_ps            每股净资产
#   gross_margin       毛利率（百分点）
#   dividend_yield     股息率（百分点）
#   beta / w52         波动率、52 周高低点相对现价的比例
#   volume             日均成交量
_DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "AAPL": {"price": 182.50, "shares": 15.615e9, "revenue": 416e9, "net": 105e9,
             "fcf": 112e9, "debt": 108e9, "cash": 61.5e9, "book_ps": 4.04,
             "gross_margin": 45.7, "dividend_yield": 0.52, "beta": 1.18,
             "w52": (1.09, 0.68), "volume": 48.23e6},
    "MSFT": {"price": 430.00, "shares": 7.43e9, "revenue": 245e9, "net": 88e9,
             "fcf": 74e9, "debt": 100e9, "cash": 80e9, "book_ps": 45.0,
             "gross_margin": 70.0, "dividend_yield": 0.72, "beta": 0.89,
             "w52": (1.12, 0.74), "volume": 22e6},
    "NVDA": {"price": 135.00, "shares": 24.5e9, "revenue": 130e9, "net": 62e9,
             "fcf": 58e9, "debt": 10e9, "cash": 38e9, "book_ps": 3.2,
             "gross_margin": 75.0, "dividend_yield": 0.03, "beta": 1.72,
             "w52": (1.35, 0.42), "volume": 250e6},
    "TSLA": {"price": 250.00, "shares": 3.2e9, "revenue": 98e9, "net": 10e9,
             "fcf": 3e9, "debt": 13e9, "cash": 36e9, "book_ps": 22.5,
             "gross_margin": 18.0, "dividend_yield": 0.0, "beta": 2.31,
             "w52": (1.65, 0.58), "volume": 90e6},
    "AMZN": {"price": 205.00, "shares": 10.6e9, "revenue": 620e9, "net": 55e9,
             "fcf": 38e9, "debt": 130e9, "cash": 90e9, "book_ps": 25.0,
             "gross_margin": 48.0, "dividend_yield": 0.0, "beta": 1.15,
             "w52": (1.24, 0.81), "volume": 40e6},
    "0700.HK": {"price": 380.00, "shares": 9.2e9, "revenue": 700e9, "net": 160e9,
                "fcf": 150e9, "debt": 350e9, "cash": 200e9, "book_ps": 110.0,
                "gross_margin": 53.0, "dividend_yield": 0.92, "beta": 0.79,
                "w52": (1.18, 0.86), "volume": 15e6},
    "9988.HK": {"price": 85.00, "shares": 19.0e9, "revenue": 940e9, "net": 80e9,
                "fcf": 120e9, "debt": 150e9, "cash": 400e9, "book_ps": 55.0,
                "gross_margin": 40.0, "dividend_yield": 1.25, "beta": 1.35,
                "w52": (1.42, 0.51), "volume": 30e6},
    "600519.SS": {"price": 1500.00, "shares": 1.256e9, "revenue": 170e9, "net": 86e9,
                  "fcf": 80e9, "debt": 0.5e9, "cash": 200e9, "book_ps": 250.0,
                  "gross_margin": 91.0, "dividend_yield": 2.12, "beta": 0.68,
                  "w52": (1.06, 0.93), "volume": 3.5e6},
    "000001.SZ": {"price": 11.50, "shares": 19.4e9, "revenue": 165e9, "net": 46e9,
                  "fcf": 40e9, "debt": 500e9, "cash": 300e9, "book_ps": 21.5,
                  "gross_margin": 55.0, "dividend_yield": 5.12, "beta": 0.85,
                  "w52": (1.31, 0.64), "volume": 60e6},
    "830799.BJ": {"price": 18.50, "shares": 0.2e9, "revenue": 0.8e9, "net": 0.12e9,
                  "fcf": 0.1e9, "debt": 0.05e9, "cash": 0.2e9, "book_ps": 6.0,
                  "gross_margin": 45.0, "dividend_yield": 1.38, "beta": 1.02,
                  "w52": (1.55, 0.39), "volume": 1.2e6},
}

# 基础财报序列（AAPL）。其他标的按画像里的收入/净利润/FCF 比例缩放这条曲线，
# 既保留历史增长形状，又让最新一期与画像对齐。
_BASE_LATEST = _DEMO_FINANCIALS[0]

_DEMO_INSTRUMENTS_BY_TICKER = {row["ticker"]: row for row in _DEMO_INSTRUMENTS}

_EBITDA_RATIO = 0.343
_OPERATING_RATIO = 0.68  # 营业利润约为毛利润的 68%
_CAPEX_RATIO = 0.029  # 资本开支约为营业收入的 2.9%


def _build_sample(profile: dict[str, Any], instrument: dict[str, Any]) -> dict[str, Any]:
    """由画像推导出行情字段，保证市值/估值比率与财报口径自洽。"""
    price = profile["price"]
    shares = profile["shares"]
    revenue = profile["revenue"]
    eps = profile["net"] / shares
    market_cap = price * shares
    ebitda = revenue * _EBITDA_RATIO
    per_share_value = price / eps
    hi_ratio, lo_ratio = profile["w52"]
    # 每个标的固定的涨跌幅（-3% ~ +3%），避免所有标的都显示同一个涨跌
    change_ratio = 1 + ((zlib.crc32(instrument["ticker"].encode("utf-8")) % 61) - 30) / 1000

    return {
        "shortName": instrument["name"],
        "currency": instrument["currency"],
        "currentPrice": price,
        "previousClose": round(price / change_ratio, 4),
        "regularMarketDayHigh": round(price * 1.0142, 4),
        "regularMarketDayLow": round(price * 0.9775, 4),
        "open": round(price * 0.9868, 4),
        "marketCap": market_cap,
        "trailingPE": per_share_value,
        "forwardPE": per_share_value / 1.18,
        "trailingEps": eps,
        "dividendYield": profile["dividend_yield"] / 100,
        "beta": profile["beta"],
        "fiftyTwoWeekHigh": round(price * hi_ratio, 4),
        "fiftyTwoWeekLow": round(price * lo_ratio, 4),
        "regularMarketVolume": profile["volume"],
        "sharesOutstanding": shares,
        "priceToBook": price / profile["book_ps"],
        "priceToSalesTrailing12Months": market_cap / revenue,
        "enterpriseToEbitda": (market_cap + profile["debt"] - profile["cash"]) / ebitda,
        "pegRatio": per_share_value / 14.3,
        "totalDebt": profile["debt"],
        "totalCash": profile["cash"],
        "totalRevenue": revenue,
        "ebitda": ebitda,
        "bookValue": profile["book_ps"],
    }


_DEMO_SAMPLES = {
    ticker: _build_sample(profile, _DEMO_INSTRUMENTS_BY_TICKER[ticker])
    for ticker, profile in _DEMO_PROFILES.items()
}

# 演示汇率：各币种对 CNY 的中间价（1 单位外币 = X 人民币）。
# 只维护对 CNY 的一组，其他货币对按交叉汇率推导，不会出现互相矛盾的汇率。
_DEMO_FX_TO_CNY = {"USD": 7.10, "HKD": 0.91, "CNY": 1.0}

# 各周期生成的交易日数量（约数，按每年 252 个交易日折算）
_PERIOD_BARS = {
    "1mo": 22,
    "3mo": 66,
    "6mo": 130,
    "1y": 252,
    "3y": 756,
    "5y": 1260,
    "max": 2520,
}


def _trading_days(count: int, end: date) -> list[date]:
    """从 end 往前取 count 个工作日（跳过周末），升序返回。

    不生成周末的合成交易日——图表不应出现数据源没有的日期（FR-CHART-05）。
    """
    days: list[date] = []
    current = end
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return list(reversed(days))


def _aggregate(daily: list[Bar], key) -> list[Bar]:
    """把日线聚合成周线/月线：开=首日开，高=最高，低=最低，收=末日收，量=合计。"""
    buckets: dict[Any, list[Bar]] = {}
    order: list[Any] = []
    for bar in daily:
        k = key(bar.date)
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(bar)

    merged: list[Bar] = []
    for k in order:
        group = buckets[k]
        highs = [b.high for b in group if b.high is not None]
        lows = [b.low for b in group if b.low is not None]
        volumes = [b.volume for b in group if b.volume is not None]
        merged.append(
            Bar(
                date=group[-1].date,
                open=group[0].open,
                high=max(highs) if highs else None,
                low=min(lows) if lows else None,
                close=group[-1].close,
                volume=sum(volumes) if volumes else None,
            )
        )
    return merged


class DemoProvider:
    """离线样本数据源。"""

    name: ClassVar[str] = "demo"
    markets: ClassVar[set[str]] = {Market.US.value, Market.HK.value, Market.CN.value}

    def search(self, query: str) -> list[Instrument]:
        q = (query or "").strip()
        if not q:
            return []
        upper = q.upper()
        lowered = q.lower()

        hits: list[Instrument] = []
        for row in _DEMO_INSTRUMENTS:
            if upper == row["ticker"] or lowered in row["name"].lower():
                hits.append(
                    Instrument(
                        ticker=row["ticker"],
                        name=row["name"],
                        market=row["market"],
                        exchange=row["exchange"],
                        currency=row["currency"],
                        kind=InstrumentKind.EQUITY,
                        provider=self.name,
                    )
                )

        # 纯数字 A 股代码：提示补交易所后缀
        info = parse_ticker(q)
        if info.needs_suffix and not hits:
            hits.append(
                Instrument(
                    ticker=info.ticker,
                    name=info.ticker,
                    market=info.market,
                    exchange=None,
                    currency="CNY",
                    kind=InstrumentKind.EQUITY,
                    provider=self.name,
                    source_meta={
                        "note": f"A 股代码通常需要补交易所后缀（{info.suffix_suggestion}）",
                        "suffix_suggestion": info.suffix_suggestion,
                    },
                )
            )
        return hits

    # ------------------------------------------------------------------
    def get_fx_rate(self, base: str, quote: str) -> float | None:
        """演示汇率：1 单位 base 折合多少 quote；币种未知返回 None。"""
        to_cny_base = _DEMO_FX_TO_CNY.get((base or "").strip().upper())
        to_cny_quote = _DEMO_FX_TO_CNY.get((quote or "").strip().upper())
        if to_cny_base is None or to_cny_quote is None:
            return None
        return to_cny_base / to_cny_quote

    def _sample(self, ticker: str) -> dict[str, Any]:
        """取该代码的样本数据；未知代码抛 TickerNotFound。

        演示模式也不给不存在的代码编造数据（FR-SEARCH-05）。
        """
        symbol = (ticker or "").strip().upper()
        row = _DEMO_SAMPLES.get(symbol)
        if row is None:
            raise TickerNotFound(symbol)
        return row

    def get_quote(self, ticker: str) -> Quote:
        info = self._sample(ticker)
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
        """生成合成行情。

        先生成日线（只落在工作日上，不插值周末——FR-CHART-05），
        周线/月线由日线聚合得到，保证 OHLC 与成交量口径一致。
        """
        sample = self._sample(ticker)
        symbol = (ticker or "DEMO").upper()
        profile = _DEMO_PROFILES[symbol]

        count = _PERIOD_BARS.get(period, 252)
        dates = _trading_days(count, date.today())
        # 每个标的独立但稳定的随机序列
        rng = random.Random(zlib.crc32(symbol.encode("utf-8")))

        closes: list[float] = [sample["currentPrice"] * 0.72]
        for i in range(1, count):
            drift = 0.0016 + rng.gauss(0, 0.011) + 0.02 * math.sin(i / 23.0) / 100
            closes.append(closes[-1] * (1 + drift))

        # 整体缩放，使最后一天收盘等于演示报价
        scale = sample["currentPrice"] / closes[-1]
        closes = [c * scale for c in closes]

        daily: list[Bar] = []
        for i, day in enumerate(dates):
            close = closes[i]
            open_price = closes[i - 1] if i else close * (1 - rng.uniform(0, 0.006))
            high = max(open_price, close) * (1 + rng.uniform(0.001, 0.006))
            low = min(open_price, close) * (1 - rng.uniform(0.001, 0.006))
            daily.append(
                Bar(
                    date=day,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=int(profile["volume"] * (0.6 + rng.random() * 0.8)),
                )
            )

        if interval == "1wk":
            return _aggregate(daily, lambda d: d.isocalendar()[:2])
        if interval == "1mo":
            return _aggregate(daily, lambda d: (d.year, d.month))
        return daily

    def get_financials(self, ticker: str, period: str = "annual", limit: int = 5) -> Financials:
        sample = self._sample(ticker)
        symbol = (ticker or "DEMO").upper()
        profile = _DEMO_PROFILES[symbol]
        shares = profile["shares"]
        net_ratio = profile["net"] / _BASE_LATEST["net_income"]
        fcf_ratio = profile["fcf"] / _BASE_LATEST["free_cash_flow"]
        gross_margin = profile["gross_margin"] / 100
        # 每个标的的收入增速略有差异（-4%~+4% 每年，按代码散列固定）：
        # 最新财年仍等于画像收入，只调整历史年份，避免所有标的的营收增速一模一样。
        growth_drift = ((zlib.crc32(symbol.encode("utf-8")) % 9) - 4) / 100

        years: list[FinancialYear] = []
        for index, item in enumerate(_DEMO_FINANCIALS[:limit]):
            revenue = (
                profile["revenue"]
                * (item["revenue"] / _BASE_LATEST["revenue"])
                * (1 + growth_drift) ** index
            )
            net_income = item["net_income"] * net_ratio
            free_cash_flow = item["free_cash_flow"] * fcf_ratio
            capex = -revenue * _CAPEX_RATIO
            years.append(
                FinancialYear(
                    year=item["year"],
                    period_end=date(item["year"], 12, 31),
                    revenue=revenue,
                    gross_profit=revenue * gross_margin,
                    operating_income=revenue * gross_margin * _OPERATING_RATIO,
                    net_income=net_income,
                    eps=round(net_income / shares, 4),
                    operating_cash_flow=free_cash_flow - capex,
                    capex=capex,
                    free_cash_flow=free_cash_flow,
                    total_debt=profile["debt"],
                    total_cash=profile["cash"],
                    total_equity=shares * profile["book_ps"],
                    shares_outstanding=shares,
                    accounts_receivable=revenue * 0.14,
                    inventory=revenue * 0.05,
                )
            )
        return Financials(
            ticker=symbol,
            currency=sample["currency"],
            period=period,
            years=years,
            provider=self.name,
        )

    def get_news(self, ticker: str) -> list[NewsItem]:
        sample = self._sample(ticker)
        symbol = (ticker or "DEMO").upper()
        now = datetime.now(UTC)
        return [
            NewsItem(
                title=f"{sample['shortName']} 发布季度业绩，收入同比增长 8%（演示数据）",
                url=None,
                source="演示数据源",
                kind="news",
                published_at=now - timedelta(hours=5),
            ),
            NewsItem(
                title=f"{symbol} 宣布回购计划，金额 50 亿美元（演示数据）",
                url=None,
                source="演示数据源",
                kind="announcement",
                published_at=now - timedelta(days=1, hours=3),
            ),
        ]

    def get_calendar(self, ticker: str) -> CalendarInfo | None:
        self._sample(ticker)
        return CalendarInfo(earnings_date=date.today() + timedelta(days=21))
