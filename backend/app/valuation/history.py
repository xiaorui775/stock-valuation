"""历史估值分位：纯计算，无 I/O（FR-VAL-11）。

所有函数在样本不足或输入缺失时返回 `None`，不填充、不插值。
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

#: 样本少于该值时不给出分位数——极少数点算出来的分位没有解释力。
MIN_SAMPLES = 20

#: PRD 要求的五个分位点。
DEFAULT_POINTS = (10, 25, 50, 75, 90)


def percentile(values: Sequence[float], point: float) -> float | None:
    """线性插值分位数，与 numpy 默认口径一致。"""
    ordered = sorted(values)
    if not ordered or not 0 <= point <= 100:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * point / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def percentiles(
    values: Sequence[float], points: Sequence[float] = DEFAULT_POINTS
) -> dict[str, float] | None:
    """返回 `{"p10": ..., "p50": ...}`；样本不足返回 None。"""
    if len(values) < MIN_SAMPLES:
        return None
    return {f"p{int(p)}": percentile(values, p) for p in points}


def percentile_rank(values: Sequence[float], current: float | None) -> float | None:
    """当前值在样本中的分位（0–100）：小于等于当前值的样本占比。"""
    if current is None or len(values) < MIN_SAMPLES:
        return None
    below = sum(1 for value in values if value <= current)
    return below / len(values) * 100


def window_start(as_of: date, years: int) -> date:
    """窗口起点：`as_of` 往前推 `years` 年（2/29 归到 2/28）。"""
    try:
        return as_of.replace(year=as_of.year - years)
    except ValueError:
        return as_of.replace(year=as_of.year - years, day=28)
