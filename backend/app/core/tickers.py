"""代码规范化与市场识别。

规则（对应 PRD FR-SEARCH-02）：
- `AAPL` / `MSFT` → 美股（US）
- `0700.HK` → 港股（HK）
- `600519.SS` / `000001.SZ` / `830799.BJ` → A 股（CN）
- 纯 6 位数字 → A 股候选（需补交易所后缀）

大小写与前后空格一律容错。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.providers.models import Market

# A 股交易所后缀。6 位代码首字决定交易所，但同一代码可能跨所，故只做候选提示。
CN_SUFFIX_HINT = {
    "6": ".SS",  # 上海
    "9": ".SS",  # 上海 B 股
    "0": ".SZ",  # 深圳
    "3": ".SZ",  # 深圳创业板
    "2": ".SZ",  # 深圳 B 股
    "4": ".BJ",  # 北京
    "8": ".BJ",  # 北京
}

CN_SUFFIXES = (".SS", ".SZ", ".BJ")
HK_SUFFIXES = (".HK",)

_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-^=]*$")


@dataclass(frozen=True)
class TickerInfo:
    """规范化后的代码及其市场归属。"""

    ticker: str
    market: Market
    suffix_suggestion: str | None = None
    """当用户只输入纯数字 A 股代码时，提示应补的交易所后缀。"""

    @property
    def needs_suffix(self) -> bool:
        return self.suffix_suggestion is not None


def normalize_ticker(raw: str) -> str:
    """去空格、转大写。"""
    return (raw or "").strip().upper()


def detect_market(ticker: str) -> Market:
    """按代码后缀判断市场：.SS/.SZ/.BJ → CN，.HK → HK，其余 → US。

    纯 6 位数字按 A 股候选处理（对应 PRD FR-SEARCH-02），以便路由到 akshare；
    交易所后缀仍由调用方/用户确认。
    """
    t = normalize_ticker(ticker)
    if t.endswith(CN_SUFFIXES):
        return Market.CN
    if t.endswith(HK_SUFFIXES):
        return Market.HK
    if t.isdigit() and len(t) == 6:
        return Market.CN
    return Market.US


def parse_ticker(raw: str) -> TickerInfo:
    """解析用户输入的代码，返回规范化结果与市场归属。

    纯 6 位数字（例如 `600519`）判为 A 股候选，并给出应补的后缀建议；
    不做自动补全，因为同一代码可能同时存在于不同交易所。
    """
    t = normalize_ticker(raw)
    if not t:
        return TickerInfo(ticker="", market=Market.UNKNOWN)

    market = detect_market(t)
    if market is Market.CN or market is Market.HK:
        if t.isdigit() and len(t) == 6 and market is Market.CN:
            suffix = CN_SUFFIX_HINT.get(t[0])
            return TickerInfo(
                ticker=t,
                market=Market.CN,
                suffix_suggestion=suffix,
            )
        return TickerInfo(ticker=t, market=market)

    if t.isdigit() and len(t) == 6:
        suffix = CN_SUFFIX_HINT.get(t[0])
        return TickerInfo(
            ticker=t,
            market=Market.CN,
            suffix_suggestion=suffix,
        )

    return TickerInfo(ticker=t, market=market)


def is_code_like(raw: str) -> bool:
    """判断输入是否长得像代码（而非公司名称）。"""
    t = normalize_ticker(raw)
    if not t:
        return False
    if t.isdigit():
        return len(t) == 6
    return bool(_CODE_RE.match(t))


def looks_like_name(raw: str) -> bool:
    """判断输入是否像公司名称（含 CJK 或空格，且不像代码）。"""
    t = (raw or "").strip()
    if not t:
        return False
    has_cjk = any("一" <= ch <= "鿿" for ch in t)
    return not (is_code_like(t) and not has_cjk)


def market_label(market: Market | str | None) -> str:
    """市场的中文标签。"""
    if market is None:
        return "未知"
    value = market.value if isinstance(market, Market) else str(market)
    return {
        Market.US.value: "美股",
        Market.HK.value: "港股",
        Market.CN.value: "A股",
        Market.UNKNOWN.value: "未知",
    }.get(value, "未知")


def exchange_hint(ticker: str) -> str | None:
    """从代码后缀推断交易所名称。"""
    t = normalize_ticker(ticker)
    if t.endswith(".SS"):
        return "上交所"
    if t.endswith(".SZ"):
        return "深交所"
    if t.endswith(".BJ"):
        return "北交所"
    if t.endswith(".HK"):
        return "港交所"
    return None
