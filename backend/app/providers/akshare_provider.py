"""akshare Provider（A 股行情/财务/新闻公告）。

数据源选型（实测 2026-11，北京网络环境）：
- 实时行情：新浪财经 hq.sinajs.cn（`sh600519` + `sh600519_i` 扩展行情），稳定且字段全。
- 历史行情：akshare `stock_zh_a_hist`（东财 push2his，前复权 qfq，支持日/周/月）；
  失败时降级 `stock_zh_a_daily`（新浪，仅日线）。
- 财务报表：akshare `stock_{profit,balance,cash_flow}_sheet_by_yearly_em`（东财 emweb 主机，
  稳定），字段映射见 PRD §12.2。
- 新闻：akshare `stock_news_em`；公告：akshare `stock_zh_a_disclosure_report_cninfo`。

东财 push2 行情主机对高频访问限流严重，故实时行情不走 push2。
所有失败统一抛 `ProviderUnavailable` / `TickerNotFound`，由注册表降级处理。
"""
from __future__ import annotations

import math
import re
import urllib.request
from datetime import UTC, date, datetime
from typing import Any, ClassVar, Optional

from app.core.tickers import exchange_hint, normalize_ticker
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


def _num(value: Any) -> Optional[float]:
    """把 pandas / numpy 标量安全转成 float，缺失（NaN）返回 None。"""
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        from pandas import Timestamp

        return Timestamp(str(value)).date()
    except Exception:
        return None


def _parse_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def strip_cn_suffix(ticker: str) -> str:
    """`600519.SS` → `600519`；无后缀的 6 位数字原样返回。"""
    t = normalize_ticker(ticker)
    code = t.split(".")[0]
    return code if re.fullmatch(r"\d{6}", code) else t


# ----------------------------------------------------------------------
# 新浪实时行情
# ----------------------------------------------------------------------
_SINA_QUOTE_FIELD = {
    # sh600519 主行情 34 字段：0 名称 1 今开 2 昨收 3 现价 4 最高 5 最低
    #   8 成交量(股) 9 成交额(元) 30 日期 31 时间
    # sh600519_i 扩展：3 EPS-TTM 5 每股净资产 7 总股本(万股) 11 货币
    #   24 「52周最高|52周最低」 37 营业收入TTM(元)
}


def _sina_symbol(ticker: str) -> str:
    """`600519.SS` → `sh600519`，`000001.SZ` → `sz000001`，`920000.BJ` → `bj920000`。

    无后缀时按首数字猜交易所（6/9 → 沪，4/8 → 北，其余 → 深）。
    """
    t = normalize_ticker(ticker)
    code = strip_cn_suffix(t)
    if t.endswith(".SS"):
        return f"sh{code}"
    if t.endswith(".SZ"):
        return f"sz{code}"
    if t.endswith(".BJ"):
        return f"bj{code}"
    if re.fullmatch(r"\d{6}", code):
        first = code[0]
        if first in "69":
            return f"sh{code}"
        if first in "48":
            return f"bj{code}"
        return f"sz{code}"
    return code


def _sina_symbol_to_ticker(symbol: str) -> str:
    """`sh600519` → `600519.SS`：把新浪代码还原成带交易所后缀的完整代码。"""
    m = re.fullmatch(r"(sh|sz|bj)(\d{6})", symbol)
    if not m:
        return symbol
    return f"{m.group(2)}.{m.group(1).upper()}"


def _fetch_sina(symbols: list[str]) -> dict[str, list[str]]:
    """请求新浪 hq 接口，返回 symbol → 字段列表。失败抛 ProviderUnavailable。"""
    url = "https://hq.sinajs.cn/list=" + ",".join(symbols)
    request = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            text = resp.read().decode("gbk", errors="replace")
    except Exception as exc:
        raise ProviderUnavailable(f"新浪行情接口不可用：{exc}") from exc
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = re.match(r'var hq_str_(\w+)="([^"]*)"', line)
        if m:
            out[m.group(1)] = m.group(2).split(",")
    if not out or all(not f or not f[0] for f in out.values()):
        raise TickerNotFound(",".join(symbols))
    return out


# ----------------------------------------------------------------------
# 财务字段映射（东财 emweb 年度报表，PRD §12.2）
# ----------------------------------------------------------------------
_PROFIT_FIELDS = {
    "revenue": ["TOTAL_OPERATE_INCOME"],
    "operating_income": ["OPERATE_PROFIT"],
    "net_income": ["PARENT_NETPROFIT", "NETPROFIT"],
    "eps": ["DILUTED_EPS", "BASIC_EPS"],
}
_BALANCE_FIELDS = {
    "total_debt": ["TOTAL_LIABILITIES"],
    "total_cash": ["MONETARYFUNDS"],
    "total_equity": ["TOTAL_PARENT_EQUITY", "TOTAL_EQUITY"],
    "shares_outstanding": ["SHARE_CAPITAL"],
    "accounts_receivable": ["ACCOUNTS_RECE"],
    "inventory": ["INVENTORY"],
}
_CASHFLOW_FIELDS = {
    "operating_cash_flow": ["NETCASH_OPERATE"],
    "capex": ["CONSTRUCT_LONG_ASSET"],
}


def _sheet_value(df: Any, row: Any, field: str) -> Optional[float]:
    if df is None or row is None:
        return None
    return _num(df.loc[row, field]) if field in getattr(df, "columns", []) else None


class AkshareProvider:
    name: ClassVar[str] = "akshare"
    markets: ClassVar[set[str]] = {Market.CN.value}

    def __init__(self) -> None:
        self._ak: Any = None

    def _module(self):
        if self._ak is None:
            try:
                import akshare as ak
            except Exception as exc:
                raise ProviderUnavailable(f"akshare 不可用：{exc}") from exc
            try:
                # 用户代理会切断东财连接：强制直连（None 时 requests 仍读环境变量）
                ak.set_proxies({})
            except Exception:  # noqa: S110 - set_proxies 失败不影响主流程
                pass
            self._ak = ak
        return self._ak

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------
    def search(self, query: str) -> list[Instrument]:
        """A 股搜索：名称检索（东财搜索接口），失败退化为新浪行情探测 + 代码精确匹配。"""
        query = (query or "").strip()
        if not query:
            return []
        # 允许用户输入带后缀的代码（如 600519.SS），先剥离后缀再检索。
        code_query = strip_cn_suffix(query)
        try:
            df = self._module().stock_info_a_code_name()
            mask = df["code"].astype(str).str.contains(code_query, na=False) | df[
                "name"
            ].astype(str).str.contains(query, na=False)
            hit = df[mask]
            results = [
                Instrument(
                    ticker=f"{row.code}.{'SS' if str(row.code).startswith(('6', '9')) else 'BJ' if str(row.code)[0] in '48' else 'SZ'}",
                    name=row.name,
                    market=Market.CN,
                    currency="CNY",
                    kind=InstrumentKind.EQUITY,
                    provider=self.name,
                )
                for row in hit.head(10).itertuples()
            ]
            if results:
                return results
        except Exception as exc:
            # 上游字段变化等意外错误不应中断搜索；但记录以便排查。
            import logging

            logging.getLogger("akshare").warning("akshare_search_failed: %s", exc)
        return self._search_by_quote(query)

    def _search_by_quote(self, query: str) -> list[Instrument]:
        code = normalize_ticker(query)
        m = re.fullmatch(r"(\d{6})(\.(SS|SZ|BJ))?", code)
        if not m:
            return []
        code6 = m.group(1)
        suffix = m.group(2) or _guess_suffix(code6)
        if suffix is None:
            return []
        try:
            fields = _fetch_sina([_sina_symbol(code6 + suffix)])[_sina_symbol(code6 + suffix)]
        except ProviderUnavailable:
            return []
        except TickerNotFound:
            return []
        if not fields or not fields[0]:
            return []
        return [
            Instrument(
                ticker=code6 + suffix,
                name=fields[0],
                market=Market.CN,
                exchange=exchange_hint(code6 + suffix),
                currency="CNY",
                kind=InstrumentKind.EQUITY,
                provider=self.name,
            )
        ]

    # ------------------------------------------------------------------
    # 实时行情（新浪）
    # ------------------------------------------------------------------
    def get_quote(self, ticker: str) -> Quote:
        symbol = _sina_symbol(ticker)
        quotes = _fetch_sina([symbol, symbol + "_i"])
        main = quotes.get(symbol)
        if not main or not main[0]:
            raise TickerNotFound(ticker)
        # 统一返回带交易所后缀的完整代码（000725 → 000725.SZ），
        # 后续财务/新闻接口依赖后缀判断交易所，保存自选也以此为键。
        full_ticker = _sina_symbol_to_ticker(symbol)
        ext = quotes.get(symbol + "_i", [])

        name = main[0]
        price = _num(main[3]) if len(main) > 3 else None
        prev = _num(main[2]) if len(main) > 2 else None
        change = price - prev if price is not None and prev is not None else None

        def extv(i: int):
            return _num(ext[i]) if len(ext) > i else None

        shares_wan = extv(7)  # 总股本，万股
        shares = shares_wan * 10_000 if shares_wan else None
        bvps = extv(5)
        eps_ttm = extv(3)
        revenue_ttm = _num(ext[37]) if len(ext) > 37 else None
        market_cap = price * shares if price is not None and shares else None

        currency = str(ext[11]) if len(ext) > 11 and ext[11] else "CNY"
        week52 = ext[24].split("|") if len(ext) > 24 else []

        quote = Quote(
            ticker=full_ticker,
            name=name,
            currency=currency,
            market=Market.CN,
            exchange=exchange_hint(ticker),
            price=price,
            previous_close=prev,
            change=change,
            change_pct=(change / prev * 100) if change is not None and prev else None,
            day_high=_num(main[4]) if len(main) > 4 else None,
            day_low=_num(main[5]) if len(main) > 5 else None,
            open_price=_num(main[1]) if len(main) > 1 else None,
            volume=_num(main[8]) if len(main) > 8 else None,
            week52_high=_num(week52[0]) if len(week52) > 1 else None,
            week52_low=_num(week52[1]) if len(week52) > 1 else None,
            eps_ttm=eps_ttm,
            book_value_per_share=bvps,
            shares_outstanding=shares,
            market_cap=market_cap,
            pe_ttm=(price / eps_ttm) if (price and eps_ttm) else None,
            price_to_book=(price / bvps) if (price and bvps) else None,
            price_to_sales=(market_cap / revenue_ttm) if (market_cap and revenue_ttm) else None,
            total_revenue=revenue_ttm,
            as_of=_sina_as_of(main[30], main[31]) if len(main) > 31 else None,
            provider=self.name,
        )
        quote.missing_fields = _missing_fields(quote)
        return quote

    # ------------------------------------------------------------------
    # 历史行情
    # ------------------------------------------------------------------
    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> list[Bar]:
        ak = self._module()
        code = strip_cn_suffix(ticker)
        start, end = _period_range(period)
        em_period = {"1d": "daily", "1wk": "weekly", "1mo": "monthly"}.get(interval, "daily")
        try:
            df = ak.stock_zh_a_hist(
                symbol=code, period=em_period, start_date=start, end_date=end, adjust="qfq"
            )
        except Exception:
            df = None
        if df is None or df.empty:
            return self._history_sina(code, start, end)
        return _bars_from_em(df)

    def _history_sina(self, code: str, start: str, end: str) -> list[Bar]:
        """东财历史接口失败时的降级：新浪日线（无周/月聚合）。"""
        ak = self._module()
        symbol = _sina_symbol(code)
        if not re.fullmatch(r"(sh|sz|bj)\d{6}", symbol):
            raise TickerNotFound(code)
        try:
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
        except Exception as exc:
            raise ProviderUnavailable(f"历史行情获取失败：{exc}") from exc
        bars: list[Bar] = []
        for row in df.itertuples():
            close = _num(row.close)
            if close is None:
                continue
            bars.append(
                Bar(
                    date=_to_date(row.date),
                    open=_num(row.open),
                    high=_num(row.high),
                    low=_num(row.low),
                    close=close,
                    volume=_num(row.volume),
                )
            )
        if not bars:
            raise TickerNotFound(code)
        return bars

    # ------------------------------------------------------------------
    # 财务报表
    # ------------------------------------------------------------------
    def get_financials(self, ticker: str, period: str = "annual", limit: int = 5) -> Financials:
        ak = self._module()
        code = strip_cn_suffix(ticker)
        symbol = _em_symbol(ticker)
        try:
            profit = ak.stock_profit_sheet_by_yearly_em(symbol=symbol)
            balance = ak.stock_balance_sheet_by_yearly_em(symbol=symbol)
            cashflow = ak.stock_cash_flow_sheet_by_yearly_em(symbol=symbol)
        except Exception as exc:
            raise ProviderUnavailable(f"财务报表获取失败：{exc}") from exc
        if profit is None or profit.empty:
            raise TickerNotFound(code)

        profit = profit.set_index("REPORT_DATE")
        balance = balance.set_index("REPORT_DATE") if balance is not None else None
        cashflow = cashflow.set_index("REPORT_DATE") if cashflow is not None else None

        years: list[FinancialYear] = []
        for report_date in profit.index[:limit]:
            prow = profit.loc[report_date]
            brow = balance.loc[report_date] if balance is not None and report_date in balance.index else None
            crow = cashflow.loc[report_date] if cashflow is not None and report_date in cashflow.index else None

            def pick(source, fields: dict[str, list[str]]):
                """fields: 统一字段名 → 东财列名候选列表，取第一个非缺失值。"""
                if source is None:
                    return {name: None for name in fields}
                out = {}
                for name, columns in fields.items():
                    value = None
                    for col in columns:
                        value = _num(source.get(col))
                        if value is not None:
                            break
                    out[name] = value
                return out

            income = pick(prow, _PROFIT_FIELDS)
            bal = pick(brow, _BALANCE_FIELDS)
            flow = pick(crow, _CASHFLOW_FIELDS)
            revenue = income["revenue"]
            cost = _num(prow.get("OPERATE_COST"))
            gross = revenue - cost if revenue is not None and cost is not None else None
            ocf, capex = flow["operating_cash_flow"], flow["capex"]
            fcf = ocf - capex if (ocf is not None and capex is not None) else None
            years.append(
                FinancialYear(
                    year=_report_year(report_date),
                    period_end=_to_date(report_date),
                    revenue=revenue,
                    gross_profit=gross,
                    operating_income=income["operating_income"],
                    net_income=income["net_income"],
                    eps=income["eps"],
                    operating_cash_flow=ocf,
                    capex=capex,
                    free_cash_flow=fcf,
                    total_debt=bal["total_debt"],
                    total_cash=bal["total_cash"],
                    total_equity=bal["total_equity"],
                    shares_outstanding=bal["shares_outstanding"],
                    accounts_receivable=bal["accounts_receivable"],
                    inventory=bal["inventory"],
                )
            )
        if not years:
            raise TickerNotFound(code)
        return Financials(
            ticker=_sina_symbol_to_ticker(_sina_symbol(ticker)),
            currency="CNY",
            period=period,
            years=years,
            provider=self.name,
        )

    # ------------------------------------------------------------------
    # 新闻与公告
    # ------------------------------------------------------------------
    def get_news(self, ticker: str) -> list[NewsItem]:
        ak = self._module()
        code = strip_cn_suffix(ticker)
        try:
            news = ak.stock_news_em(symbol=code)
        except Exception as exc:
            raise ProviderUnavailable(f"新闻获取失败：{exc}") from exc
        items = [
            NewsItem(
                title=str(row["新闻标题"]),
                url=str(row["新闻链接"]),
                source=str(row["文章来源"]),
                kind="news",
                published_at=_parse_time(row["发布时间"]),
            )
            for row in news.to_dict("records")
            if isinstance(row.get("新闻标题"), str) and row["新闻标题"].strip()
        ]
        try:
            from datetime import timedelta

            end = date.today().strftime("%Y%m%d")
            start = (date.today() - timedelta(days=90)).strftime("%Y%m%d")
            disc = ak.stock_zh_a_disclosure_report_cninfo(symbol=code, start_date=start, end_date=end)
            items.extend(
                NewsItem(
                    title=str(row["公告标题"]),
                    url=str(row["公告链接"]),
                    source="巨潮资讯",
                    kind="announcement",
                    published_at=_parse_time(str(row["公告时间"])),
                )
                for row in disc.to_dict("records")
                if isinstance(row.get("公告标题"), str) and row["公告标题"].strip()
            )
        except Exception:  # noqa: S110 - 公告是增强信息，拿不到就只返回新闻
            pass
        items.sort(key=lambda i: i.published_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        return items

    def get_calendar(self, ticker: str) -> CalendarInfo | None:
        return None  # akshare 无直接财报日历接口，保持 None


def _guess_suffix(code: str) -> Optional[str]:
    from app.core.tickers import CN_SUFFIX_HINT

    hint = CN_SUFFIX_HINT.get(code[0]) if code else None
    if hint == ".SS":
        return ".SS"
    if hint in (".SZ", ".BJ"):
        return hint
    return hint


def _em_symbol(ticker: str) -> str:
    """`600519.SS` → `SH600519`（东财 emweb 报表接口的市场前缀）。

    裸 6 位码按首数字猜交易所，避免深市/北市股票被默认当作上海。
    """
    t = normalize_ticker(ticker)
    code = strip_cn_suffix(t)
    if t.endswith(".SZ"):
        return f"SZ{code}"
    if t.endswith(".BJ"):
        return f"BJ{code}"
    if t.endswith(".SS"):
        return f"SH{code}"
    return _sina_symbol(code).upper()


def _report_year(report_date: str) -> int:
    try:
        return int(str(report_date)[:4])
    except ValueError:
        return _to_date(report_date).year  # type: ignore[union-attr]


def _sina_as_of(d: str, t: str) -> Optional[datetime]:
    try:
        return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def _period_range(period: str) -> tuple[str, str]:
    """把 period 转成东财接口的 start_date/end_date。"""
    days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "3y": 1095, "5y": 1825, "max": 11000}
    from datetime import timedelta

    start = date.today() - timedelta(days=days.get(period, 365))
    return start.strftime("%Y%m%d"), date.today().strftime("%Y%m%d")


def _bars_from_em(df: Any, klt: int = 0) -> list[Bar]:
    """东财历史行情 DataFrame → 统一 Bar 列表；周/月线逐根已是聚合后的数据。"""
    bars: list[Bar] = []
    for row in df.itertuples():
        close = _num(row.收盘)
        if close is None:
            continue
        bars.append(
            Bar(
                date=_to_date(row.日期),
                open=_num(row.开盘),
                high=_num(row.最高),
                low=_num(row.最低),
                close=close,
                volume=_num(row.成交量),
            )
        )
    if not bars:
        raise TickerNotFound("history")
    return bars


def _missing_fields(quote: Quote) -> list[str]:
    important = [
        "price",
        "previous_close",
        "market_cap",
        "pe_ttm",
        "eps_ttm",
        "shares_outstanding",
    ]
    return [n for n in important if getattr(quote, n, None) is None]
