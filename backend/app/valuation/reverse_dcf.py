"""反向 DCF：用二分法求解当前股价隐含的阶段一增速。"""
from __future__ import annotations

from typing import Optional

from app.valuation.dcf import dcf_value


def implied_growth(
    price: Optional[float],
    base_fcf: Optional[float],
    years1: int,
    terminal_growth_pct: float,
    discount_pct: float,
    total_debt: Optional[float],
    total_cash: Optional[float],
    shares: Optional[float],
    low: float = -50.0,
    high: float = 100.0,
    tolerance: float = 0.01,
) -> Optional[dict]:
    """求 g 使得 DCF 每股价值等于 price。

    低增速端价值低于现价、高增速端价值高于现价时才存在解；
    否则返回 None（市场预期超出可解范围，如 FCF 为负）。
    """
    if price is None or base_fcf is None or shares in (None, 0):
        return None

    def value_at(g: float) -> Optional[float]:
        res = dcf_value(
            base_fcf, g, years1, terminal_growth_pct, discount_pct,
            total_debt, total_cash, shares,
        )
        return res["per_share"] if res else None

    v_low = value_at(low)
    v_high = value_at(high)
    if v_low is None or v_high is None:
        return None

    target = price
    if v_low > target:
        return {"implied_growth": None, "reason": "在可解区间内，即使最低增速的估值也高于现价"}
    if v_high < target:
        return {"implied_growth": None, "reason": "在可解区间内，即使最高增速的估值也低于现价"}

    lo, hi = low, high
    for _ in range(200):
        mid = (lo + hi) / 2
        v_mid = value_at(mid)
        if v_mid is None:
            return None
        if abs(v_mid - target) < 1e-6 or (hi - lo) < tolerance:
            return {
                "implied_growth": mid,
                "value_at_solution": v_mid,
                "range": [low, high],
            }
        if v_mid < target:
            lo = mid
        else:
            hi = mid
    return {
        "implied_growth": (lo + hi) / 2,
        "value_at_solution": value_at((lo + hi) / 2),
        "range": [low, high],
    }
