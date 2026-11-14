"""规则化财务解读（§5.6）。

10 条确定性规则：输入财年序列与行情快照，输出事实陈述。纯计算，无 I/O，
相同输入必然产生相同输出。规则只在数据可算时触发，缺字段则进入「未覆盖项」。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from app.providers.models import FinancialYear, Quote

LEVEL_ORDER = {"alert": 0, "watch": 1, "info": 2}


class SkipRule(Exception):
    """规则无法计算（缺字段、分母为 0）。"""


@dataclass(frozen=True)
class Rule:
    rule_id: str
    name: str
    evaluate: Callable[[list[FinancialYear], Optional[Quote]], Optional[dict]]


# ----------------------------------------------------------------------
# 工具
# ----------------------------------------------------------------------

def _yoy(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous) * 100


def _cagr(years: list[FinancialYear], field: str, span: int = 3) -> Optional[float]:
    if len(years) <= span:
        return None
    latest = getattr(years[0], field)
    base = getattr(years[span], field)
    if latest is None or base is None or latest <= 0 or base <= 0:
        return None
    return ((latest / base) ** (1 / span) - 1) * 100


def _amount(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1e12:
        return f"{value / 1e12:.2f} 万亿"
    if magnitude >= 1e8:
        return f"{value / 1e8:.2f} 亿"
    if magnitude >= 1e4:
        return f"{value / 1e4:.2f} 万"
    return f"{value:.2f}"


def _item(
    rule_id: str,
    name: str,
    level: str,
    title: str,
    detail: str,
    formula: str,
    value: Optional[float],
    period: Optional[str],
) -> dict:
    return {
        "rule": rule_id,
        "name": name,
        "level": level,
        "title": title,
        "detail": detail,
        "formula": formula,
        "value": None if value is None else round(value, 4),
        "period": period,
    }


def _margin(year: FinancialYear, field: str) -> Optional[float]:
    revenue = year.revenue
    value = getattr(year, field)
    if revenue is None or revenue == 0 or value is None:
        return None
    return value / revenue * 100


# ----------------------------------------------------------------------
# 规则
# ----------------------------------------------------------------------

def revenue_growth(
    years: list[FinancialYear], quote: Optional[Quote]
) -> Optional[dict]:
    if len(years) < 2:
        raise SkipRule("需要至少两个财年")
    latest, previous = years[0], years[1]
    change = _yoy(latest.revenue, previous.revenue)
    if change is None:
        raise SkipRule("缺少营业收入或上期为 0")

    if change > 20:
        level = "info"
        title = f"营业收入同比增长 {change:.1f}%，处于高增长区间"
    elif change < 0:
        level = "watch"
        title = f"营业收入同比下滑 {abs(change):.1f}%"
    else:
        return None

    detail = (
        f"{previous.year} → {latest.year}："
        f"{_amount(previous.revenue)} → {_amount(latest.revenue)}"
    )
    cagr = _cagr(years, "revenue")
    if cagr is not None:
        detail += f"；3 年 CAGR {cagr:.1f}%"
    return _item(
        "revenue_growth",
        "营收增长",
        level,
        title,
        detail,
        "YoY = (本期 − 上期) / |上期|",
        change,
        f"{previous.year}→{latest.year}",
    )


def _margin_trend(
    field: str, rule_id: str, name: str, label: str, numerator: str
) -> Callable[[list[FinancialYear], Optional[Quote]], Optional[dict]]:
    """连续两个年度下降且累计超过 3 个百分点。"""

    def evaluate(
        years: list[FinancialYear], quote: Optional[Quote]
    ) -> Optional[dict]:
        if len(years) < 3:
            raise SkipRule("需要至少三个财年")
        margins = [_margin(year, field) for year in years[:3]]
        if any(value is None for value in margins):
            raise SkipRule(f"缺少{label}或营业收入")
        newest, middle, oldest = margins  # type: ignore[misc]
        if not (newest < middle < oldest):
            return None
        drop = oldest - newest
        if drop <= 3:
            return None
        return _item(
            rule_id,
            name,
            "watch",
            f"{label}连续两年下降，累计 {drop:.1f} 个百分点",
            f"{years[2].year} → {years[0].year}："
            f"{oldest:.1f}% → {middle:.1f}% → {newest:.1f}%",
            f"{label} = {numerator} / 营业收入",
            drop,
            f"{years[2].year}→{years[0].year}",
        )

    return evaluate


gross_margin_trend = _margin_trend(
    "gross_profit", "gross_margin_trend", "毛利率趋势", "毛利率", "毛利润"
)
operating_margin_trend = _margin_trend(
    "operating_income",
    "operating_margin_trend",
    "营业利润率趋势",
    "营业利润率",
    "营业利润",
)
net_margin_trend = _margin_trend(
    "net_income", "net_margin_trend", "净利率趋势", "净利率", "净利润"
)


def cash_quality(years: list[FinancialYear], quote: Optional[Quote]) -> Optional[dict]:
    if len(years) < 2:
        raise SkipRule("需要至少两个财年")
    ratios: list[float] = []
    for year in years[:2]:
        if year.free_cash_flow is None or year.net_income is None:
            raise SkipRule("缺少自由现金流或净利润")
        if year.net_income <= 0:
            raise SkipRule("净利润为负，现金含量无经济含义")
        ratios.append(year.free_cash_flow / year.net_income * 100)
    if not all(ratio < 50 for ratio in ratios):
        return None
    newest, previous = years[0], years[1]
    return _item(
        "cash_quality",
        "现金流质量",
        "alert",
        "自由现金流连续两年不足净利润的一半",
        f"{previous.year}：{ratios[1]:.1f}%；{newest.year}：{ratios[0]:.1f}%",
        "现金含量 = 自由现金流 / 净利润",
        ratios[0],
        f"{previous.year}→{newest.year}",
    )


def accrual_anomaly(
    years: list[FinancialYear], quote: Optional[Quote]
) -> Optional[dict]:
    if len(years) < 2:
        raise SkipRule("需要至少两个财年")
    latest, previous = years[0], years[1]
    income_growth = _yoy(latest.net_income, previous.net_income)
    cash_growth = _yoy(
        latest.operating_cash_flow, previous.operating_cash_flow
    )
    if income_growth is None or cash_growth is None:
        raise SkipRule("缺少净利润或经营现金流")
    gap = income_growth - cash_growth
    if gap <= 20:
        return None
    return _item(
        "accrual_anomaly",
        "应计异常",
        "alert",
        f"净利润增速比经营现金流增速高 {gap:.1f} 个百分点",
        f"{previous.year} → {latest.year}：净利润 {income_growth:+.1f}%，"
        f"经营现金流 {cash_growth:+.1f}%",
        "差额 = 净利润增速 − 经营现金流增速",
        gap,
        f"{previous.year}→{latest.year}",
    )


def leverage(years: list[FinancialYear], quote: Optional[Quote]) -> Optional[dict]:
    if not years:
        raise SkipRule("缺少财年数据")
    latest = years[0]
    flags: list[str] = []
    computed = False

    if (
        latest.total_debt is not None
        and latest.total_equity is not None
        and latest.total_equity > 0
    ):
        computed = True
        ratio = latest.total_debt / latest.total_equity
        if ratio > 2:
            flags.append(f"总债务 / 股东权益 = {ratio:.2f}（阈值 2.0）")

    if (
        latest.total_debt is not None
        and latest.total_cash is not None
        and quote is not None
        and quote.ebitda not in (None, 0)
    ):
        computed = True
        net_debt = latest.total_debt - latest.total_cash
        ratio = net_debt / quote.ebitda
        if ratio > 4:
            flags.append(f"净债务 / EBITDA = {ratio:.2f}（阈值 4.0）")

    if not computed:
        raise SkipRule("缺少债务、股东权益或 EBITDA 数据")
    if not flags:
        return None
    return _item(
        "leverage",
        "杠杆",
        "watch",
        "杠杆水平高于常见阈值",
        f"{latest.year} 财年：" + "；".join(flags),
        "总债务 / 股东权益；净债务 / EBITDA",
        None,
        str(latest.year),
    )


def dilution(years: list[FinancialYear], quote: Optional[Quote]) -> Optional[dict]:
    if len(years) < 2:
        raise SkipRule("需要至少两个财年")
    latest, previous = years[0], years[1]
    change = _yoy(latest.shares_outstanding, previous.shares_outstanding)
    if change is None:
        raise SkipRule("缺少总股本或上期为 0")
    if change <= 2:
        return None
    return _item(
        "dilution",
        "股本稀释",
        "watch",
        f"总股本同比增长 {change:.1f}%",
        f"{previous.year} → {latest.year}："
        f"{_amount(previous.shares_outstanding)}股 → "
        f"{_amount(latest.shares_outstanding)}股",
        "股本 YoY = (本期 − 上期) / |上期|",
        change,
        f"{previous.year}→{latest.year}",
    )


def gross_margin_expansion(
    years: list[FinancialYear], quote: Optional[Quote]
) -> Optional[dict]:
    if len(years) < 2:
        raise SkipRule("需要至少两个财年")
    newest = _margin(years[0], "gross_profit")
    previous = _margin(years[1], "gross_profit")
    if newest is None or previous is None:
        raise SkipRule("缺少毛利润或营业收入")
    change = newest - previous
    if change <= 3:
        return None
    return _item(
        "gross_margin_expansion",
        "毛利率扩张",
        "info",
        f"毛利率同比提升 {change:.1f} 个百分点",
        f"{years[1].year} → {years[0].year}：{previous:.1f}% → {newest:.1f}%",
        "毛利率 = 毛利润 / 营业收入",
        change,
        f"{years[1].year}→{years[0].year}",
    )


def receivables_inventory(
    years: list[FinancialYear], quote: Optional[Quote]
) -> Optional[dict]:
    if len(years) < 2:
        raise SkipRule("需要至少两个财年")
    latest, previous = years[0], years[1]
    revenue_growth = _yoy(latest.revenue, previous.revenue)
    if revenue_growth is None:
        raise SkipRule("缺少营业收入")
    flags: list[str] = []
    available = False
    for field, label in (
        ("accounts_receivable", "应收账款"),
        ("inventory", "存货"),
    ):
        growth = _yoy(getattr(latest, field), getattr(previous, field))
        if growth is None:
            continue
        available = True
        gap = growth - revenue_growth
        if gap > 20:
            flags.append(
                f"{label}增速 {growth:.1f}%，高于营收增速 "
                f"{revenue_growth:.1f}%（差 {gap:.1f} 个百分点）"
            )
    if not available:
        raise SkipRule("数据源未提供应收账款与存货字段")
    if not flags:
        return None
    return _item(
        "receivables_inventory",
        "营收与应收/存货",
        "watch",
        "应收账款或存货增速明显高于营收",
        f"{previous.year} → {latest.year}：" + "；".join(flags),
        "差额 = 应收/存货增速 − 营收增速",
        None,
        f"{previous.year}→{latest.year}",
    )


RULES: tuple[Rule, ...] = (
    Rule("revenue_growth", "营收增长", revenue_growth),
    Rule("gross_margin_trend", "毛利率趋势", gross_margin_trend),
    Rule("operating_margin_trend", "营业利润率趋势", operating_margin_trend),
    Rule("net_margin_trend", "净利率趋势", net_margin_trend),
    Rule("cash_quality", "现金流质量", cash_quality),
    Rule("accrual_anomaly", "应计异常", accrual_anomaly),
    Rule("leverage", "杠杆", leverage),
    Rule("dilution", "股本稀释", dilution),
    Rule("gross_margin_expansion", "毛利率扩张", gross_margin_expansion),
    Rule("receivables_inventory", "营收与应收/存货", receivables_inventory),
)


def analyze(
    years: list[FinancialYear], quote: Optional[Quote] = None
) -> dict:
    """执行全部规则，按级别排序并汇总未覆盖项。"""
    ordered = sorted(years, key=lambda year: year.year, reverse=True)
    items: list[dict] = []
    uncovered: list[dict] = []

    if not ordered:
        return {
            "items": [],
            "uncovered": [
                {"rule": "all", "name": "全部规则", "reason": "缺少财年数据"}
            ],
            "summary": "没有可用的财年数据，无法进行财务解读。",
            "fiscal_year": None,
        }

    for rule in RULES:
        try:
            result = rule.evaluate(ordered, quote)
        except SkipRule as reason:
            uncovered.append(
                {"rule": rule.rule_id, "name": rule.name, "reason": str(reason)}
            )
            continue
        if result is not None:
            items.append(result)

    items.sort(key=lambda item: LEVEL_ORDER.get(item["level"], 9))

    if items:
        counts = {level: 0 for level in LEVEL_ORDER}
        for item in items:
            counts[item["level"]] = counts.get(item["level"], 0) + 1
        summary = (
            f"共 {len(items)} 条事实：alert {counts['alert']} 条、"
            f"watch {counts['watch']} 条、info {counts['info']} 条。"
        )
    else:
        summary = "未发现显著异常。"

    return {
        "items": items,
        "uncovered": uncovered,
        "summary": summary,
        "fiscal_year": ordered[0].year,
    }
