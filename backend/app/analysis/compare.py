"""多股对比的纯计算（§5.10 FR-CMP-02 / 03）。

指标方向在服务端固定下来（估值越低越好、增速越高越好），前端不再各自判断，
避免同一张表里「最优」的口径不一致。缺失值不参与最优/最差评选。
"""
from __future__ import annotations

from dataclasses import dataclass

HIGHER = "higher"
LOWER = "lower"


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    unit: str
    direction: str | None = None


# 顺序即表格行顺序（与 PRD 5.10 FR-CMP-03 一致）
METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("market_cap", "市值", "currency"),
    MetricSpec("revenue_growth", "营收增速", "pct", HIGHER),
    MetricSpec("gross_margin", "毛利率", "pct", HIGHER),
    MetricSpec("net_margin", "净利率", "pct", HIGHER),
    MetricSpec("pe_ttm", "P/E", "x", LOWER),
    MetricSpec("forward_pe", "Forward P/E", "x", LOWER),
    MetricSpec("peg", "PEG", "x", LOWER),
    MetricSpec("price_to_book", "P/B", "x", LOWER),
    MetricSpec("price_to_sales", "P/S", "x", LOWER),
    MetricSpec("ev_ebitda", "EV/EBITDA", "x", LOWER),
    MetricSpec("dividend_yield", "股息率", "pct", HIGHER),
    MetricSpec("fcf_yield", "FCF Yield", "pct", HIGHER),
    MetricSpec("dcf_upside_pct", "DCF 上行空间", "pct", HIGHER),
    MetricSpec("beta", "Beta", "x"),
)


def best_worst(
    values: dict[str, float | None], direction: str | None
) -> tuple[str | None, str | None]:
    """按方向选出最优/最差；缺失值不参与。

    少于两个有效值、没有方向、或所有值相等时返回 (None, None)——「都一样」时
    标出最优是没有信息量的误导。并列时取输入顺序里的第一个（结果可复现）。
    """
    if direction is None:
        return None, None
    items = [(ticker, value) for ticker, value in values.items() if value is not None]
    if len(items) < 2:
        return None, None
    low, high = min(items, key=lambda item: item[1]), max(items, key=lambda item: item[1])
    if low[1] == high[1]:
        return None, None
    return (high[0], low[0]) if direction == HIGHER else (low[0], high[0])


def normalize_series(
    points: list[tuple[str, float]], base: float | None = None
) -> list[dict[str, float | str]]:
    """把收盘价序列归一化为起点 = 100。

    `points` 为 (日期字符串, 收盘价) 升序；调用方负责去掉缺失收盘价的点。
    base 缺省取第一个点；base 缺失或为 0 时返回空序列（无法归一化就不画）。
    """
    if not points:
        return []
    if base is None:
        base = points[0][1]
    if not base:
        return []
    return [{"date": day, "value": close / base * 100} for day, close in points]
