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


def ddm_three_stage(
    price: Optional[float],
    dividend_yield_pct: Optional[float],
    growth1_pct: float,
    years1: int,
    fade_years: int,
    terminal_growth_pct: float,
    discount_pct: float,
) -> Optional[dict]:
    """三阶段股利折现：显式增长期 → 增速线性衰减期 → 永续期。

    与 `dcf_three_stage` 同一套阶段定义，只是现金流换成股利（DPS = 股价 × 股息率）。
    仅适用于有股息的公司；股息率为 0 或缺失时返回 None（FR-VAL-12）。
    """
    if price is None or not dividend_yield_pct or dividend_yield_pct <= 0:
        return None
    if years1 < 1 or fade_years < 0:
        return None
    r = discount_pct / 100.0
    g1 = growth1_pct / 100.0
    gt = terminal_growth_pct / 100.0
    if r <= gt or r <= -1:
        return None

    dps = price * dividend_yield_pct / 100.0
    t = 0
    pv = 0.0
    dividend = dps

    # 阶段一：恒定增速
    for _ in range(years1):
        t += 1
        dividend = dps * (1 + g1) ** t
        pv += dividend / (1 + r) ** t
    pv_explicit = pv

    # 阶段二：增速线性衰减到 terminal_growth
    if fade_years:
        step = (g1 - gt) / fade_years
        for i in range(1, fade_years + 1):
            t += 1
            dividend = dividend * (1 + (g1 - step * i))
            pv += dividend / (1 + r) ** t
    pv_fade = pv - pv_explicit

    # 阶段三：永续
    terminal = dividend * (1 + gt) / (r - gt)
    pv_terminal = terminal / (1 + r) ** t
    total = pv + pv_terminal
    return {
        "per_share": total,
        "dps": dps,
        "pv_explicit": pv_explicit,
        "pv_fade": pv_fade,
        "pv_terminal": pv_terminal,
        "terminal_ratio": (pv_terminal / total) if total else None,
        "years": t,
    }
