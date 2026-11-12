"""Gordon 股利增长模型。"""
from __future__ import annotations

from typing import Optional


def ddm_value(
    price: Optional[float],
    dividend_yield_pct: Optional[float],
    growth_pct: float,
    discount_pct: float,
) -> Optional[float]:
    """Gordon 模型：价值 = DPS×(1+g) / (r − g)，DPS = 股价 × 股息率。

    dividend_yield_pct 为百分数（10 表示 10%）。
    """
    if not dividend_yield_pct or dividend_yield_pct <= 0 or price is None:
        return None
    r, g = discount_pct / 100.0, growth_pct / 100.0
    if r <= g:
        return None
    dps = price * dividend_yield_pct / 100.0
    return dps * (1 + g) / (r - g)
