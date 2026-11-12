"""数据层：通过 yfinance 获取行情、历史价格与财务报表。

- 内存缓存，TTL 约 300 秒
- 环境变量 STOCKVAL_DEMO=1 时启用演示模式，返回内置样本数据（不访问网络）
- 上游失败或代码无效时抛出 DataError，由 API 层转成干净的 JSON 错误
"""

import os
import time

import pandas as pd

CACHE_TTL = 300  # 秒
_cache = {}


class DataError(Exception):
    """数据不可用（代码无效、上游失败等）。"""


DEMO_MODE = os.environ.get("STOCKVAL_DEMO") == "1"


def _cache_get(key):
    item = _cache.get(key)
    if item and time.time() - item[0] < CACHE_TTL:
        return item[1]
    return None


def _cache_set(key, value):
    _cache[key] = (time.time(), value)
    return value


def _num(value):
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


def _normalize_yield(raw):
    """yfinance 的 dividendYield 在不同版本里有小数和百分数两种口径，统一成百分数。"""
    if raw is None:
        return None
    raw = float(raw)
    # 0.0052 -> 0.52%；若本身已经是 0.52 这种百分数形式则保持
    return raw * 100 if raw < 0.15 else raw


# ---------------------------------------------------------------------------
# 演示数据（仅 STOCKVAL_DEMO=1 时使用），一家虚构公司 "示例科技"
# ---------------------------------------------------------------------------

_DEMO_INFO = {
    "symbol": "DEMO",
    "shortName": "示例科技（演示数据）",
    "currency": "USD",
    "currentPrice": 182.50,
    "previousClose": 179.20,
    "regularMarketDayHigh": 185.10,
    "regularMarketDayLow": 178.40,
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

# 演示用年度报表：{指标: {年份: 金额}}，年份新→旧
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


def _demo_quote(ticker):
    info = dict(_DEMO_INFO)
    info["symbol"] = (ticker or "DEMO").upper()
    prev = info["previousClose"]
    price = info["currentPrice"]
    return {
        "ticker": info["symbol"],
        "name": info["shortName"],
        "currency": info["currency"],
        "demo": True,
        "price": price,
        "previous_close": prev,
        "change": price - prev,
        "change_pct": (price - prev) / prev * 100,
        "day_high": info["regularMarketDayHigh"],
        "day_low": info["regularMarketDayLow"],
        "market_cap": info["marketCap"],
        "pe_ttm": info["trailingPE"],
        "forward_pe": info["forwardPE"],
        "eps_ttm": info["trailingEps"],
        "dividend_yield": _normalize_yield(info["dividendYield"]),
        "beta": info["beta"],
        "week52_high": info["fiftyTwoWeekHigh"],
        "week52_low": info["fiftyTwoWeekLow"],
        "volume": info["regularMarketVolume"],
        "shares_outstanding": info["sharesOutstanding"],
        "price_to_book": info["priceToBook"],
        "price_to_sales": info["priceToSalesTrailing12Months"],
        "ev_ebitda": info["enterpriseToEbitda"],
        "peg": info["pegRatio"],
        "total_debt": info["totalDebt"],
        "total_cash": info["totalCash"],
        "total_revenue": info["totalRevenue"],
        "ebitda": info["ebitda"],
        "book_value_per_share": info["bookValue"],
    }


def _demo_history():
    import math
    import random

    random.seed(42)
    points = []
    price = 130.0
    today = pd.Timestamp.today().normalize()
    days = pd.bdate_range(end=today, periods=252)
    for i, d in enumerate(days):
        price *= 1 + 0.0016 + random.gauss(0, 0.011) + 0.02 * math.sin(i / 23.0) / 100
        points.append({"date": d.strftime("%Y-%m-%d"), "close": round(price, 2)})
    # 让最后一天收盘与演示报价一致
    points[-1]["close"] = _DEMO_INFO["currentPrice"]
    return points


# ---------------------------------------------------------------------------
# 真实数据（yfinance）
# ---------------------------------------------------------------------------

def _ticker_obj(ticker):
    import yfinance as yf

    return yf.Ticker(ticker)


def _fetch_info(ticker):
    try:
        t = _ticker_obj(ticker)
        info = t.info or {}
    except Exception as exc:  # 上游网络/解析失败
        raise DataError(f"数据服务暂时不可用：{exc}") from exc
    price = _num(info.get("currentPrice") or info.get("regularMarketPrice"))
    if price is None:
        # 尝试用最近收盘价兜底
        try:
            hist = t.history(period="5d")
            if not hist.empty:
                price = _num(hist["Close"].iloc[-1])
        except Exception:
            price = None
    if price is None:
        raise DataError(f"找不到股票代码 {ticker}，或该代码暂无行情数据")
    return info, price


def get_quote(ticker):
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise DataError("缺少股票代码")
    if DEMO_MODE:
        return _demo_quote(ticker)
    key = ("quote", ticker)
    cached = _cache_get(key)
    if cached:
        return cached
    info, price = _fetch_info(ticker)
    prev = _num(info.get("previousClose"))
    change = price - prev if prev else None
    quote = {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "currency": info.get("currency") or "USD",
        "demo": False,
        "price": price,
        "previous_close": prev,
        "change": change,
        "change_pct": (change / prev * 100) if (change is not None and prev) else None,
        "day_high": _num(info.get("regularMarketDayHigh") or info.get("dayHigh")),
        "day_low": _num(info.get("regularMarketDayLow") or info.get("dayLow")),
        "market_cap": _num(info.get("marketCap")),
        "pe_ttm": _num(info.get("trailingPE")),
        "forward_pe": _num(info.get("forwardPE")),
        "eps_ttm": _num(info.get("trailingEps")),
        "dividend_yield": _normalize_yield(_num(info.get("dividendYield"))),
        "beta": _num(info.get("beta")),
        "week52_high": _num(info.get("fiftyTwoWeekHigh")),
        "week52_low": _num(info.get("fiftyTwoWeekLow")),
        "volume": _num(info.get("regularMarketVolume") or info.get("volume")),
        "shares_outstanding": _num(info.get("sharesOutstanding")),
        "price_to_book": _num(info.get("priceToBook")),
        "price_to_sales": _num(info.get("priceToSalesTrailing12Months")),
        "ev_ebitda": _num(info.get("enterpriseToEbitda")),
        "peg": _num(info.get("pegRatio")),
        "total_debt": _num(info.get("totalDebt")),
        "total_cash": _num(info.get("totalCash")),
        "total_revenue": _num(info.get("totalRevenue")),
        "ebitda": _num(info.get("ebitda")),
        "book_value_per_share": _num(info.get("bookValue")),
    }
    return _cache_set(key, quote)


def get_history(ticker):
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise DataError("缺少股票代码")
    if DEMO_MODE:
        return _demo_history()
    key = ("history", ticker)
    cached = _cache_get(key)
    if cached:
        return cached
    try:
        hist = _ticker_obj(ticker).history(period="1y", auto_adjust=False)
    except Exception as exc:
        raise DataError(f"历史价格获取失败：{exc}") from exc
    if hist is None or hist.empty:
        raise DataError(f"股票代码 {ticker} 暂无历史价格")
    points = [
        {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 4)}
        for idx, row in hist.iterrows()
        if not pd.isna(row["Close"])
    ]
    return _cache_set(key, points)


def _row(df, *names):
    """按多个候选行名取一行（Series），都找不到返回 None。"""
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def _statement_years(df, limit=4):
    """返回报表列（日期）从新到旧的前 limit 个。"""
    if df is None or df.empty:
        return []
    cols = sorted(df.columns, reverse=True)
    return cols[:limit]


def get_financials(ticker):
    """最近 4 个财年：营收、毛利、营业利润、净利润、自由现金流。"""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise DataError("缺少股票代码")
    if DEMO_MODE:
        return {"ticker": ticker, "demo": True, "years": _DEMO_FINANCIALS}
    key = ("financials", ticker)
    cached = _cache_get(key)
    if cached:
        return cached
    try:
        t = _ticker_obj(ticker)
        income = t.income_stmt
        cashflow = t.cashflow
        balance = t.balance_sheet
    except Exception as exc:
        raise DataError(f"财务报表获取失败：{exc}") from exc
    if income is None or income.empty:
        raise DataError(f"股票代码 {ticker} 暂无财务报表数据")

    rev = _row(income, "Total Revenue")
    gross = _row(income, "Gross Profit")
    oper = _row(income, "Operating Income")
    net = _row(income, "Net Income", "Net Income Common Stockholders")
    ocf = _row(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = _row(cashflow, "Capital Expenditure")
    fcf_row = _row(cashflow, "Free Cash Flow")
    debt_row = _row(balance, "Total Debt")
    cash_row = _row(balance, "Cash And Cash Equivalents",
                    "Cash Cash Equivalents And Short Term Investments")
    equity_row = _row(balance, "Stockholders Equity",
                      "Total Equity Gross Minority Interest", "Common Stock Equity")

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

    years = []
    for col in _statement_years(income):
        years.append({
            "year": pd.Timestamp(col).year,
            "revenue": val(rev, col),
            "gross_profit": val(gross, col),
            "operating_income": val(oper, col),
            "net_income": val(net, col),
            "free_cash_flow": fcf(col),
        })
    if not years:
        raise DataError(f"股票代码 {ticker} 暂无财务报表数据")

    balance_latest = {}
    bcols = _statement_years(balance, limit=1)
    if bcols:
        c0 = bcols[0]
        balance_latest = {
            "total_debt": val(debt_row, c0),
            "total_cash": val(cash_row, c0),
            "total_equity": val(equity_row, c0),
        }
    result = {"ticker": ticker, "demo": False, "years": years,
              "balance_latest": balance_latest}
    return _cache_set(key, result)
