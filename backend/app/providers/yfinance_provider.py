"""yfinance 数据源适配器。

负责把 yfinance 的 info / 财务报表 / 新闻转换为统一模型。
不负责缓存与降级——那是 service 层的事。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar, Optional

import pandas as pd

from app.providers.base import (
    ProviderUnavailable,
    TickerNotFound,
    detect_market,
)
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


def _num(value: Any) -> Optional[float]:
    """把 pandas / numpy 标量安全转成 float，缺失返回 None。"""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_yield(raw: Optional[float]) -> Optional[float]:
    """yfinance 的 dividendYield 在不同版本里有小数和百分数两种口径，统一成百分数。"""
    if raw is None:
        return None
    raw = float(raw)
    # 0.0052 -> 0.52%；若本身已经是 0.52 这种百分数形式则保持
    return raw * 100 if raw < 0.15 else raw


class YFinanceProvider:
    name: ClassVar[str] = "yfinance"
    markets: ClassVar[set[str]] = {Market.US.value, Market.HK.value}

    def __init__(self) -> None:
        self._yf = None

    def _module(self):
        if self._yf is None:
            try:
                import yfinance as yf
            except Exception as exc:  # pragma: no cover - 环境问题
                raise ProviderUnavailable(f"yfinance 不可用：{exc}") from exc
            self._yf = yf
        return self._yf

    def _ticker(self, ticker: str):
        return self._module().Ticker(ticker)

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------
    def search(self, query: str) -> list[Instrument]:
        query = (query or "").strip()
        if not query:
            return []
        try:
            yf = self._module()
            searcher = yf.Search(query, max_results=10)
            quotes = getattr(searcher, "quotes", None) or []
        except Exception:
            # 名称搜索不可用时退化为代码精确匹配
            quotes = []
        results: list[Instrument] = []
        for q in quotes:
            symbol = q.get("symbol")
            if not symbol:
                continue
            results.append(
                Instrument(
                    ticker=symbol,
                    name=q.get("shortname") or q.get("longname") or symbol,
                    market=detect_market(symbol),
                    exchange=q.get("exchange"),
                    currency=q.get("currency"),
                    provider=self.name,
                )
            )
        if not results:
            upper = query.upper()
            if upper.isalnum() and len(upper) <= 10:
                results.append(
                    Instrument(
                        ticker=upper,
                        name=upper,
                        market=detect_market(upper),
                        provider=self.name,
                        source_meta={"note": "按代码精确匹配"},
                    )
                )
        return results

    # ------------------------------------------------------------------
    # 行情
    # ------------------------------------------------------------------
    def get_quote(self, ticker: str) -> Quote:
        try:
            t = self._ticker(ticker)
            info = t.info or {}
        except Exception as exc:
            raise ProviderUnavailable(f"行情获取失败：{exc}") from exc

        price = _num(info.get("currentPrice") or info.get("regularMarketPrice"))
        if price is None:
            try:
                hist = t.history(period="5d")
                if not hist.empty:
                    price = _num(hist["Close"].iloc[-1])
            except Exception:
                price = None
        if price is None:
            raise TickerNotFound(ticker)

        prev = _num(info.get("previousClose"))
        change = (price - prev) if prev is not None else None
        as_of = _num(info.get("regularMarketTime"))
        quote = Quote(
            ticker=ticker.upper(),
            name=info.get("shortName") or info.get("longName") or ticker.upper(),
            currency=info.get("currency"),
            market=detect_market(ticker),
            price=price,
            previous_close=prev,
            change=change,
            change_pct=(change / prev * 100) if (change is not None and prev) else None,
            day_high=_num(info.get("regularMarketDayHigh") or info.get("dayHigh")),
            day_low=_num(info.get("regularMarketDayLow") or info.get("dayLow")),
            open_price=_num(info.get("regularMarketOpen") or info.get("open")),
            market_cap=_num(info.get("marketCap")),
            pe_ttm=_num(info.get("trailingPE")),
            forward_pe=_num(info.get("forwardPE")),
            eps_ttm=_num(info.get("trailingEps")),
            dividend_yield=normalize_yield(_num(info.get("dividendYield"))),
            beta=_num(info.get("beta")),
            week52_high=_num(info.get("fiftyTwoWeekHigh")),
            week52_low=_num(info.get("fiftyTwoWeekLow")),
            volume=_num(info.get("regularMarketVolume") or info.get("volume")),
            shares_outstanding=_num(info.get("sharesOutstanding")),
            price_to_book=_num(info.get("priceToBook")),
            price_to_sales=_num(info.get("priceToSalesTrailing12Months")),
            ev_ebitda=_num(info.get("enterpriseToEbitda")),
            peg=_num(info.get("pegRatio")),
            total_debt=_num(info.get("totalDebt")),
            total_cash=_num(info.get("totalCash")),
            total_revenue=_num(info.get("totalRevenue")),
            ebitda=_num(info.get("ebitda")),
            book_value_per_share=_num(info.get("bookValue")),
            as_of=datetime.fromtimestamp(as_of, tz=UTC) if as_of else None,
            provider=self.name,
        )
        quote.missing_fields = _collect_missing(quote)
        return quote

    # ------------------------------------------------------------------
    # 历史行情
    # ------------------------------------------------------------------
    def get_history(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> list[Bar]:
        try:
            hist = self._ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        except Exception as exc:
            raise ProviderUnavailable(f"历史价格获取失败：{exc}") from exc
        if hist is None or hist.empty:
            raise TickerNotFound(ticker)
        bars: list[Bar] = []
        for idx, row in hist.iterrows():
            close = _num(row.get("Close"))
            if close is None:
                continue
            bars.append(
                Bar(
                    date=pd.Timestamp(idx).date(),
                    open=_num(row.get("Open")),
                    high=_num(row.get("High")),
                    low=_num(row.get("Low")),
                    close=close,
                    volume=_num(row.get("Volume")),
                    adj_close=_num(row.get("Adj Close")) if "Adj Close" in hist.columns else None,
                )
            )
        return bars

    # ------------------------------------------------------------------
    # 财务报表
    # ------------------------------------------------------------------
    def get_financials(self, ticker: str, period: str = "annual", limit: int = 5) -> Financials:
        try:
            t = self._ticker(ticker)
            income = t.income_stmt
            cashflow = t.cashflow
            balance = t.balance_sheet
        except Exception as exc:
            raise ProviderUnavailable(f"财务报表获取失败：{exc}") from exc
        if income is None or income.empty:
            raise TickerNotFound(ticker)

        rev = _row(income, "Total Revenue")
        gross = _row(income, "Gross Profit")
        oper = _row(income, "Operating Income")
        net = _row(income, "Net Income", "Net Income Common Stockholders")
        eps = _row(income, "Diluted EPS", "Basic EPS")
        ocf = _row(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex = _row(cashflow, "Capital Expenditure")
        fcf_row = _row(cashflow, "Free Cash Flow")
        debt_row = _row(balance, "Total Debt")
        cash_row = _row(
            balance, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"
        )
        equity_row = _row(
            balance, "Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"
        )
        shares_row = _row(balance, "Ordinary Shares Number", "Share Issued")

        def val(series, col):
            if series is None or col not in series.index:
                return None
            return _num(series[col])

        def fcf(col):
            direct = val(fcf_row, col)
            if direct is not None:
                return direct
            o, c = val(ocf, col), val(capex, col)
            if o is not None and c is not None:
                return o + c  # capex 在现金流量表中通常为负数
            return None

        years: list[FinancialYear] = []
        for col in _statement_years(income, limit=limit):
            years.append(
                FinancialYear(
                    year=pd.Timestamp(col).year,
                    period_end=pd.Timestamp(col).date(),
                    revenue=val(rev, col),
                    gross_profit=val(gross, col),
                    operating_income=val(oper, col),
                    net_income=val(net, col),
                    eps=val(eps, col),
                    operating_cash_flow=val(ocf, col),
                    capex=val(capex, col),
                    free_cash_flow=fcf(col),
                    total_debt=val(debt_row, col),
                    total_cash=val(cash_row, col),
                    total_equity=val(equity_row, col),
                    shares_outstanding=val(shares_row, col),
                )
            )
        if not years:
            raise TickerNotFound(ticker)
        return Financials(
            ticker=ticker.upper(),
            currency=_num(getattr(self._ticker(ticker), "currency", None)) or None,
            period=period,
            years=years,
            provider=self.name,
        )

    # ------------------------------------------------------------------
    # 新闻与日历
    # ------------------------------------------------------------------
    def get_news(self, ticker: str) -> list[NewsItem]:
        try:
            raw = self._ticker(ticker).news or []
        except Exception as exc:
            raise ProviderUnavailable(f"新闻获取失败：{exc}") from exc
        items: list[NewsItem] = []
        for entry in raw:
            content = entry.get("content") or entry
            title = content.get("title") or entry.get("title")
            if not title:
                continue
            published = content.get("pubDate") or content.get("displayTime")
            items.append(
                NewsItem(
                    title=title,
                    url=content.get("canonicalUrl", {}).get("url")
                    if isinstance(content.get("canonicalUrl"), dict)
                    else content.get("clickThroughUrl", {}).get("url")
                    if isinstance(content.get("clickThroughUrl"), dict)
                    else entry.get("link"),
                    source=content.get("provider", {}).get("displayName")
                    if isinstance(content.get("provider"), dict)
                    else None,
                    kind="news",
                    published_at=_parse_time(published),
                )
            )
        return items

    def get_calendar(self, ticker: str) -> CalendarInfo | None:
        try:
            cal = self._ticker(ticker).calendar
        except Exception:
            return None
        if cal is None:
            return None
        earnings = None
        try:
            earnings = _to_date(cal.get("Earnings Date"))
        except Exception:
            earnings = None
        if earnings is None:
            return None
        return CalendarInfo(earnings_date=earnings)


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------

def _row(df, *names):
    """按多个候选行名取一行（Series），都找不到返回 None。"""
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def _statement_years(df, limit: int = 5):
    """返回报表列（日期）从新到旧的前 limit 个。"""
    if df is None or df.empty:
        return []
    return sorted(df.columns, reverse=True)[:limit]


def _parse_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _to_date(value: Any):
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and value:
        value = value[0]
    try:
        return pd.Timestamp(value).date()
    except Exception:
        return None


def _collect_missing(quote: Quote) -> list[str]:
    """列出行情中缺失的关键字段。"""
    important = [
        "price",
        "previous_close",
        "market_cap",
        "pe_ttm",
        "eps_ttm",
        "dividend_yield",
        "beta",
        "shares_outstanding",
        "total_debt",
        "total_cash",
    ]
    return [name for name in important if getattr(quote, name, None) is None]
