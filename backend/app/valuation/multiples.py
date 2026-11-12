"""估值倍数工具。"""
from __future__ import annotations

from typing import Optional


def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    return a / b


def fcf_yield(
    free_cash_flow: Optional[float], market_cap: Optional[float]
) -> Optional[float]:
    """FCF Yield = 自由现金流 / 市值，返回百分数。"""
    ratio = safe_div(free_cash_flow, market_cap)
    return ratio * 100 if ratio is not None else None
