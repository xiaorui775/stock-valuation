"""akshare 全球 Provider（美股/港股行情、财务、新闻）。

数据源选型（实测 2026-11，北京网络环境）：
- 美股实时行情：新浪 hq.sinajs.cn `gb_msft`，字段全（价格/涨跌/52周/市值/PE/EPS/股本）。
- 港股实时行情：新浪 `rt_hk00700`，字段含名称/开高低收/昨收/52周/成交量。
- 美股历史：akshare `stock_us_daily`（新浪，前复权）；周/月线在本地聚合。
- 港股历史：akshare `stock_hk_daily`（新浪，前复权）；周/月线在本地聚合。
- 美股财务：akshare `stock_financial_us_report_em`（东财 datacenter，三大报表 ITEM_NAME 长表）。
- 港股财务：akshare `stock_financial_hk_report_em`（同上，STD_ITEM_NAME 长表）。
- 搜索：东财 searchapi suggest（覆盖美/港/A 三市场，非 push2 主机，不受行情限流影响）。
- 新闻：akshare `stock_news_em`（东财 datacenter，美股/港股均可查）。

刻意绕开东财 push2 行情主机（stock_us_hist / stock_hk_hist）——该主机限流严重。
美股财年可能非自然年（如 MSFT 6 月截止），以 REPORT_DATE 所在年份标注。
所有失败统一抛 `ProviderUnavailable` / `TickerNotFound`，由注册表降级到 yfinance。
"""
from __future__ import annotations

import re
import urllib.request
from datetime import UTC, date, datetime, timedelta
from typing import Any, ClassVar, Optional

from app.providers.base import ProviderUnavailable, TickerNotFound
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

# 市场类型号（东财 searchapi MktNum）→ 统一市场
_EM_MKT_MARKET = {"105": Market.US, "106": Market.US, "107": Market.US, "116": Market.HK}


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hk_code(ticker: str) -> str:
    """`0700.HK` / `00700.HK` → `00700`（东财/新浪港股一律 5 位）。"""
    code = ticker.split(".")[0]
    digits = re.sub(r"\D", "", code)
    return digits.zfill(5) if digits else code


def _us_symbol(ticker: str) -> str:
    """`MSFT` → `MSFT`（akshare 美股接口用大写；新浪 gb_ 行情另行小写）。"""
    return ticker.split(".")[0].upper()


def _hk_sina_symbol(ticker: str) -> str:
    return f"rt_hk{_hk_code(ticker)}"


def _us_sina_symbol(ticker: str) -> str:
    return f"gb_{_us_symbol(ticker).lower()}"


def _fetch_sina(symbols: list[str]) -> dict[str, list[str]]:
    url = "https://hq.sinajs.cn/list=" + ",".join(symbols)
    request = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            text = resp.read().decode("gbk", errors="replace")
    except Exception as exc:
        raise ProviderUnavailable(f"新浪行情接口不可用：{exc}") from exc
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = re.match(r'var hq_str_\w+="([^"]*)"', line)
        if m:
            out.setdefault("rows", []).append(m.group(1).split(","))
    rows = out.get("rows", [])
    if not rows or all(not f or not f[0] for f in rows):
        raise TickerNotFound(",".join(symbols))
    return out


def _hk_as_of(d: str, t: str) -> Optional[datetime]:
    """`2026/11/13` + `16:08:22` → UTC datetime（北京时间 +8）。"""
    try:
        dt = datetime.strptime(f"{d} {t}", "%Y/%m/%d %H:%M:%S")
        from datetime import timezone

        return dt.replace(tzinfo=timezone(timedelta(hours=8))).astimezone(UTC)
    except (ValueError, TypeError):
        return None


def _us_as_of(text: str) -> Optional[datetime]:
    """`Nov 13 07:59PM EST` → UTC。"""
    if not text:
        return None
    for fmt in ("%b %d %I:%M%p EST", "%b %d %I:%M%p EDT"):
        try:
            dt = datetime.strptime(text.strip(), fmt)
            from datetime import timezone

            return dt.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(UTC)
        except ValueError:
            continue
    return None


def _aggregate_bars(bars: list[Bar], interval: str) -> list[Bar]:
    """把日线聚合成周线/月线。"""
    if interval == "1d" or not bars:
        return bars
    bucket: dict[str, Bar] = {}
    for bar in bars:
        if interval == "1wk":
            iso = bar.date.isocalendar()
            key = f"{iso.year}-W{iso.week:02d}"
        else:
            key = f"{bar.date.year}-{bar.date.month:02d}"
        prev = bucket.get(key)
        if prev is None:
            bucket[key] = bar.model_copy()
        else:
            prev.high = max(prev.high or bar.high or 0, bar.high) if (prev.high or bar.high) else None
            prev.low = min(prev.low, bar.low) if (prev.low is not None and bar.low is not None) else prev.low or bar.low
            prev.close = bar.close
            if prev.volume is not None and bar.volume is not None:
                prev.volume += bar.volume
            prev.date = bar.date
    return [bucket[k] for k in sorted(bucket)]


class AkshareGlobalProvider:
    """美股/港股数据源（新浪行情 + 东财 datacenter 财报/新闻），降级到 yfinance。"""

    name: ClassVar[str] = "akshare-global"
    markets: ClassVar[set[str]] = {Market.US.value, Market.HK.value}

    def __init__(self) -> None:
        self._ak: Any = None

    def _module(self):
        if self._ak is None:
            try:
                import akshare as ak
            except Exception as exc:
                raise ProviderUnavailable(f"akshare 不可用：{exc}") from exc
            try:
                ak.set_proxies({})
            except Exception:  # noqa: S110 - set_proxies 失败不影响主流程
                pass
            self._ak = ak
        return self._ak

    # ------------------------------------------------------------------
    # 搜索（东财 searchapi suggest，覆盖美/港）
    # ------------------------------------------------------------------
    def search(self, query: str) -> list[Instrument]:
        query = (query or "").strip()
        if not query:
            return []
        url = (
            "https://searchapi.eastmoney.com/api/suggest/get?input="
            + urllib.request.quote(query)
            + "&type=14&count=10"
        )
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=10) as resp:
                import json as _json

                data = _json.loads(resp.read().decode())
        except Exception as exc:
            raise ProviderUnavailable(f"搜索接口不可用：{exc}") from exc
        table = (data.get("QuotationCodeTable") or {}).get("Data") or []
        results: list[Instrument] = []
        for row in table:
            mkt = str(row.get("MktNum") or "")
            market = _EM_MKT_MARKET.get(mkt)
            if market is None:
                continue
            code = str(row.get("Code") or "")
            name = str(row.get("Name") or "")
            if not code:
                continue
            if market is Market.US:
                ticker = code.upper()
            else:
                ticker = f"{code.zfill(5)}.HK"
            results.append(
                Instrument(
                    ticker=ticker,
                    name=name,
                    market=market,
                    currency="USD" if market is Market.US else "HKD",
                    kind=InstrumentKind.EQUITY,
                    provider=self.name,
                )
            )
        return results

    # ------------------------------------------------------------------
    # 实时行情（新浪）
    # ------------------------------------------------------------------
    def get_quote(self, ticker: str) -> Quote:
        t = ticker.upper()
        if not t.isascii():
            # 名称（如「英伟达」）不是代码，直接判定为无效代码，
            # 避免把上游网络错误误报成限流。
            raise TickerNotFound(ticker)
        if t.endswith(".HK"):
            return self._hk_quote(t)
        return self._us_quote(t)

    def _hk_quote(self, ticker: str) -> Quote:
        rows = _fetch_sina([_hk_sina_symbol(ticker)])["rows"]
        f = rows[0]
        # rt_hk 字段：0 英文名 1 中文名 2 今开 3 昨收 4 最高 5 最低 6 现价
        #   7 涨跌额 8 涨跌幅% 9 买一 10 卖一 11 成交额 12 成交量(股)
        #   17 日期 18 时间 21 「52周高|52周低|52周日期」
        price = _num(f[6]) if len(f) > 6 else None
        prev = _num(f[3]) if len(f) > 3 else None
        change = _num(f[7]) if len(f) > 7 else None
        week52 = f[21].split("|") if len(f) > 21 else []
        name = (f[1] or f[0] or ticker).strip()
        quote = Quote(
            ticker=ticker,
            name=name,
            currency="HKD",
            market=Market.HK,
            exchange="HKEX",
            price=price,
            previous_close=prev,
            change=change,
            change_pct=_num(f[8]) if len(f) > 8 else None,
            day_high=_num(f[4]) if len(f) > 4 else None,
            day_low=_num(f[5]) if len(f) > 5 else None,
            open_price=_num(f[2]) if len(f) > 2 else None,
            volume=_num(f[12]) if len(f) > 12 else None,
            week52_high=_num(week52[0]) if week52 else None,
            week52_low=_num(week52[1]) if len(week52) > 1 else None,
            as_of=_hk_as_of(f[17], f[18]) if len(f) > 18 else None,
            provider=self.name,
        )
        if price and prev:
            quote.pe_ttm = None  # 新浪港股 rt_hk 无 PE 字段；不得编造
        return quote

    def _us_quote(self, ticker: str) -> Quote:
        rows = _fetch_sina([_us_sina_symbol(ticker)])["rows"]
        f = rows[0]
        # gb_ 字段：0 名称 1 现价 2 涨跌幅% 3 时间(北京) 4 涨跌额 5 开盘 6 最高
        #   7 最低 8 52周高 9 52周低 10 成交量 11 前日成交量 12 总市值
        #   13 EPS-TTM 14 PE-TTM 19 总股本 21 昨收 26 前收盘
        price = _num(f[1])
        prev = _num(f[21]) if len(f) > 21 else None
        if prev is None:
            prev = _num(f[26]) if len(f) > 26 else None
        change = _num(f[4]) if len(f) > 4 else None
        shares = _num(f[19]) if len(f) > 19 else None
        market_cap = _num(f[12]) if len(f) > 12 else None
        name = (f[0] or ticker).strip()
        quote = Quote(
            ticker=ticker,
            name=name,
            currency="USD",
            market=Market.US,
            exchange="US",
            price=price,
            previous_close=prev,
            change=change,
            change_pct=_num(f[2]) if len(f) > 2 else None,
            day_high=_num(f[6]) if len(f) > 6 else None,
            day_low=_num(f[7]) if len(f) > 7 else None,
            open_price=_num(f[5]) if len(f) > 5 else None,
            market_cap=market_cap,
            pe_ttm=_num(f[14]) if len(f) > 14 else None,
            eps_ttm=_num(f[13]) if len(f) > 13 else None,
            week52_high=_num(f[8]) if len(f) > 8 else None,
            week52_low=_num(f[9]) if len(f) > 9 else None,
            volume=_num(f[10]) if len(f) > 10 else None,
            shares_outstanding=shares,
            as_of=_hk_as_of(f[3].split(" ")[0], f[3].split(" ")[1]) if len(f) > 3 and " " in f[3] else None,
            provider=self.name,
        )
        return quote

    # ------------------------------------------------------------------
    # 历史行情（新浪日线，本地聚合周/月）
    # ------------------------------------------------------------------
    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> list[Bar]:
        if not ticker.isascii():
            raise TickerNotFound(ticker)
        ak = self._module()
        days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "3y": 1095, "5y": 1825, "max": 11000}
        span = days.get(period, 365)
        start = date.today() - timedelta(days=span)
        t = ticker.upper()
        try:
            if t.endswith(".HK"):
                df = ak.stock_hk_daily(symbol=_hk_code(t))
            else:
                df = ak.stock_us_daily(symbol=_us_symbol(t))
        except Exception as exc:
            raise ProviderUnavailable(f"历史行情获取失败：{exc}") from exc
        if df is None or df.empty:
            raise TickerNotFound(ticker)
        bars: list[Bar] = []
        for row in df.itertuples():
            close = _num(row.close)
            d = row.date
            if close is None or d is None:
                continue
            if hasattr(d, "date"):
                d = d.date()
            if d < start and span != 11000:
                continue
            bars.append(
                Bar(
                    date=d,
                    open=_num(row.open),
                    high=_num(row.high),
                    low=_num(row.low),
                    close=close,
                    volume=_num(row.volume),
                )
            )
        if not bars:
            raise TickerNotFound(ticker)
        return _aggregate_bars(bars, interval)

    # ------------------------------------------------------------------
    # 财务报表（东财 datacenter 长表 → 透视到统一模型）
    # ------------------------------------------------------------------
    def get_financials(self, ticker: str, period: str = "annual", limit: int = 5) -> Financials:
        if not ticker.isascii():
            raise TickerNotFound(ticker)
        ak = self._module()
        t = ticker.upper()
        is_hk = t.endswith(".HK")
        if is_hk:
            # HK 接口的利润表参数值是「利润表」（US 是「综合损益表」）
            specs = [
                ("利润表", _HK_INCOME_ITEMS),
                ("资产负债表", _HK_BALANCE_ITEMS),
                ("现金流量表", _HK_CASHFLOW_ITEMS),
            ]
            symbol_arg = _hk_code(t)
            date_col, item_col = "REPORT_DATE", "STD_ITEM_NAME"
            income_symbol = "利润表"
        else:
            specs = [
                ("综合损益表", _US_INCOME_ITEMS),
                ("资产负债表", _US_BALANCE_ITEMS),
                ("现金流量表", _US_CASHFLOW_ITEMS),
            ]
            symbol_arg = _us_symbol(t).upper()
            date_col, item_col = "REPORT_DATE", "ITEM_NAME"
            income_symbol = "综合损益表"

        sheets: dict[str, Any] = {}
        for report_symbol, _ in specs:
            try:
                if is_hk:
                    df = ak.stock_financial_hk_report_em(
                        stock=symbol_arg, symbol=report_symbol, indicator="年度"
                    )
                else:
                    df = ak.stock_financial_us_report_em(
                        stock=symbol_arg, symbol=report_symbol, indicator="年报"
                    )
            except Exception as exc:
                raise ProviderUnavailable(f"财务报表获取失败：{exc}") from exc
            sheets[report_symbol] = df

        income = sheets[income_symbol]
        if income is None or income.empty:
            raise TickerNotFound(ticker)

        # 长表透视：REPORT_DATE × ITEM_NAME → AMOUNT
        def pivot(df: Any) -> dict[Any, dict[str, float]]:
            out: dict[Any, dict[str, float]] = {}
            if df is None or df.empty:
                return out
            for row in df.to_dict("records"):
                d = str(row.get(date_col))[:10]
                item = str(row.get(item_col) or "").strip()
                amount = _num(row.get("AMOUNT"))
                if not item or amount is None:
                    continue
                out.setdefault(d, {})[item] = amount
            return out

        pivots = {name: pivot(df) for name, df in sheets.items()}
        dates = sorted(pivots[income_symbol].keys(), reverse=True)[:limit]
        if not dates:
            raise TickerNotFound(ticker)

        balance, cashflow = pivots["资产负债表"], pivots["现金流量表"]

        def pick(row: dict[str, float] | None, names: list[str]) -> Optional[float]:
            if not row:
                return None
            for name in names:
                if name in row:
                    return row[name]
            return None

        years: list[FinancialYear] = []
        for d in dates:
            irow, brow, crow = pivots[income_symbol].get(d), balance.get(d), cashflow.get(d)
            revenue = pick(irow, specs[0][1]["revenue"])
            cost = pick(irow, specs[0][1]["cost"])
            gross = revenue - cost if revenue is not None and cost is not None else None
            ocf = pick(crow, specs[2][1]["operating_cash_flow"])
            capex = pick(crow, specs[2][1]["capex"])
            fcf = ocf - capex if (ocf is not None and capex is not None) else None
            years.append(
                FinancialYear(
                    year=int(d[:4]),
                    period_end=_parse_date(d),
                    revenue=revenue,
                    gross_profit=gross,
                    operating_income=pick(irow, specs[0][1]["operating_income"]),
                    net_income=pick(irow, specs[0][1]["net_income"]),
                    eps=pick(irow, specs[0][1]["eps"]),
                    operating_cash_flow=ocf,
                    capex=capex,
                    free_cash_flow=fcf,
                    total_debt=pick(brow, specs[1][1]["total_debt"]),
                    total_cash=pick(brow, specs[1][1]["total_cash"]),
                    total_equity=pick(brow, specs[1][1]["total_equity"]),
                    shares_outstanding=pick(brow, specs[1][1]["shares_outstanding"]),
                    accounts_receivable=pick(brow, specs[1][1]["accounts_receivable"]),
                    inventory=pick(brow, specs[1][1]["inventory"]),
                )
            )
        return Financials(
            ticker=t,
            currency="HKD" if is_hk else "USD",
            period=period,
            years=years,
            provider=self.name,
        )

    # ------------------------------------------------------------------
    # 新闻（东财 datacenter，美/港通用）
    # ------------------------------------------------------------------
    def get_news(self, ticker: str) -> list[NewsItem]:
        if not ticker.isascii():
            raise TickerNotFound(ticker)
        ak = self._module()
        t = ticker.upper()
        code = _hk_code(t) if t.endswith(".HK") else _us_symbol(t).upper()
        try:
            df = ak.stock_news_em(symbol=code)
        except Exception as exc:
            raise ProviderUnavailable(f"新闻获取失败：{exc}") from exc
        items = [
            NewsItem(
                title=str(row["新闻标题"]),
                url=str(row["新闻链接"]),
                source=str(row["文章来源"]),
                kind="news",
                published_at=_parse_dt(row["发布时间"]),
            )
            for row in df.to_dict("records")
            if isinstance(row.get("新闻标题"), str) and row["新闻标题"].strip()
        ]
        items.sort(
            key=lambda i: i.published_at or datetime.min.replace(tzinfo=UTC), reverse=True
        )
        return items

    def get_calendar(self, ticker: str) -> CalendarInfo | None:
        return None


# ----------------------------------------------------------------------
# 东财长表 ITEM_NAME / STD_ITEM_NAME 映射
# ----------------------------------------------------------------------
_US_INCOME_ITEMS = {
    "revenue": ["营业收入", "主营收入"],
    "cost": ["营业成本", "主营成本"],
    "operating_income": ["营业利润", "经营溢利", "营业外收入"],
    "net_income": ["净利润", "归属母公司净利润"],
    "eps": ["摊薄每股收益-普通股", "基本每股收益-普通股", "摊薄每股收益", "基本每股收益", "稀释每股收益"],
}
_US_BALANCE_ITEMS = {
    "total_debt": ["总负债"],
    "total_cash": ["现金及现金等价物", "货币资金"],
    "total_equity": ["归属于母公司股东权益", "股东权益合计", "总权益"],
    "shares_outstanding": ["总股本", "股本"],
    "accounts_receivable": ["应收账款"],
    "inventory": ["存货"],
}
_US_CASHFLOW_ITEMS = {
    "operating_cash_flow": ["经营活动产生的现金流量净额"],
    "capex": ["购买固定资产", "购建固定资产、无形资产和其他长期资产支付的现金"],
}
_HK_INCOME_ITEMS = {
    "revenue": ["营业额"],
    "cost": ["经营成本", "销售成本", "经营费用"],
    "operating_income": ["经营溢利", "营运收入"],
    "net_income": ["股东应占溢利", "除税后溢利"],
    "eps": ["每股摊薄盈利", "每股基本盈利"],
}
_HK_BALANCE_ITEMS = {
    "total_debt": ["总负债"],
    "total_cash": ["现金及等价物", "现金及银行结余"],
    "total_equity": ["股东权益", "总权益"],
    "shares_outstanding": ["股本"],
    "accounts_receivable": ["应收帐款"],
    "inventory": ["存货"],
}
_HK_CASHFLOW_ITEMS = {
    "operating_cash_flow": ["经营业务现金净额", "经营产生现金"],
    "capex": ["购买固定资产", "购置物业、厂房及设备"],
}


def _parse_date(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(text[:10])
    except (ValueError, TypeError):
        return None


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None
