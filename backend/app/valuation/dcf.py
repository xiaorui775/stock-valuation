"""两阶段 / 三阶段 DCF。

纯计算函数：缺失输入或数学不成立时返回 None，绝不编造数据。
"""
from __future__ import annotations

from typing import Optional


def dcf_value(
    base_fcf: Optional[float],
    growth1_pct: float,
    years1: int,
    terminal_growth_pct: float,
    discount_pct: float,
    total_debt: Optional[float],
    total_cash: Optional[float],
    shares: Optional[float],
) -> Optional[dict]:
    """两阶段 DCF，返回每股内在价值与中间量。

    阶段一：未来 years1 年 FCF 按 growth1 增长；
    终值：TV = FCF_n × (1+gT) / (r − gT)；
    企业价值 = Σ FCF_t/(1+r)^t + TV/(1+r)^n；
    股权价值 = 企业价值 − 总债务 + 现金；每股价值 = 股权价值 / 总股数。
    """
    if base_fcf is None or shares in (None, 0):
        return None
    r = discount_pct / 100.0
    g1 = growth1_pct / 100.0
    gt = terminal_growth_pct / 100.0
    if r <= gt or r <= -1:
        return None
    pv = 0.0
    fcf = base_fcf
    for t in range(1, years1 + 1):
        fcf = base_fcf * (1 + g1) ** t
        pv += fcf / (1 + r) ** t
    terminal = fcf * (1 + gt) / (r - gt)
    pv_terminal = terminal / (1 + r) ** years1
    ev = pv + pv_terminal
    equity = ev - (total_debt or 0) + (total_cash or 0)
    per_share = equity / shares
    return {
        "per_share": per_share,
        "enterprise_value": ev,
        "equity_value": equity,
        "pv_terminal_ratio": (pv_terminal / ev) if ev else None,
    }


def dcf_three_stage(
    base_fcf: Optional[float],
    growth1_pct: float,
    years1: int,
    fade_years: int,
    terminal_growth_pct: float,
    discount_pct: float,
    total_debt: Optional[float],
    total_cash: Optional[float],
    shares: Optional[float],
) -> Optional[dict]:
    """三阶段 DCF：显式高增长期 → 增速线性衰减期 → 永续期。

    衰减期：从 growth1 线性递减到 terminal_growth，终值用衰减期最后一年的 FCF。
    """
    if base_fcf is None or shares in (None, 0):
        return None
    if years1 < 1 or fade_years < 0:
        return None
    r = discount_pct / 100.0
    g1 = growth1_pct / 100.0
    gt = terminal_growth_pct / 100.0
    if r <= gt or r <= -1:
        return None

    pv = 0.0
    fcf = base_fcf
    t = 0

    # 阶段一：恒定增速
    for _ in range(years1):
        t += 1
        fcf = base_fcf * (1 + g1) ** t
        pv += fcf / (1 + r) ** t

    # 阶段二：增速从 growth1 线性衰减到 terminal_growth
    if fade_years:
        step = (g1 - gt) / fade_years
        for i in range(1, fade_years + 1):
            t += 1
            g = g1 - step * i
            fcf = fcf * (1 + g)
            pv += fcf / (1 + r) ** t

    # 阶段三：永续
    terminal = fcf * (1 + gt) / (r - gt)
    pv_terminal = terminal / (1 + r) ** t
    ev = pv + pv_terminal
    equity = ev - (total_debt or 0) + (total_cash or 0)
    return {
        "per_share": equity / shares,
        "enterprise_value": ev,
        "equity_value": equity,
        "pv_terminal_ratio": (pv_terminal / ev) if ev else None,
        "years": t,
    }
