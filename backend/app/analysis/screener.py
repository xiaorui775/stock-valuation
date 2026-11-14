"""筛选器纯计算（§5.11 FR-SCR-02 / 03）。

规则很直白但有两个容易做错的点，这里固定下来：
- 缺失值不满足任何带边界的条件。缺 P/E 的标的不能因为「看不出问题」而进入
  P/E < 20 的结果集——筛选是「满足条件」，不是「没有违反条件」。
- 排序时缺失值永远排在最后（升序降序都一样），否则升序时 null 会被当成最小值。
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

FILTER_METRICS: tuple[str, ...] = (
    "market_cap",
    "pe_ttm",
    "forward_pe",
    "peg",
    "price_to_book",
    "price_to_sales",
    "ev_ebitda",
    "dividend_yield",
    "revenue_growth",
    "fcf_yield",
    "dcf_upside_pct",
    "beta",
)


@dataclass(frozen=True)
class Filter:
    metric: str
    minimum: float | None = None
    maximum: float | None = None


def passes(row: dict[str, Any], filters: Iterable[Filter]) -> bool:
    """所有条件都满足才通过；任一条件依赖的字段缺失则该行不通过。"""
    for rule in filters:
        value = row.get(rule.metric)
        if value is None:
            return False
        if rule.minimum is not None and value < rule.minimum:
            return False
        if rule.maximum is not None and value > rule.maximum:
            return False
    return True


def sort_rows(
    rows: list[dict[str, Any]], key: str | None, descending: bool
) -> list[dict[str, Any]]:
    """按指标排序，缺失值固定排在最后；排序是稳定的，同值保持原顺序。"""
    if key is None:
        return rows
    present = [row for row in rows if row.get(key) is not None]
    missing = [row for row in rows if row.get(key) is None]
    return sorted(present, key=lambda row: row[key], reverse=descending) + missing


def paginate(
    rows: list[dict[str, Any]], page: int, page_size: int
) -> list[dict[str, Any]]:
    start = max(0, (page - 1) * page_size)
    return rows[start : start + page_size]
