"""WACC 与 CAPM 折现率。"""
from __future__ import annotations

from typing import Optional


def capm_discount_rate(
    beta: Optional[float], risk_free: float = 4.0, erp: float = 5.0
) -> float:
    """CAPM：折现率(%) = 无风险利率 + Beta × 股权风险溢价。Beta 缺失时取 1.0。"""
    b = beta if beta is not None else 1.0
    return risk_free + b * erp


def wacc(
    risk_free: float,
    beta: Optional[float],
    erp: float,
    cost_of_debt: float,
    tax_rate: float,
    debt: Optional[float],
    equity: Optional[float],
) -> Optional[dict]:
    """加权平均资本成本。

    r_e = r_f + β × ERP
    WACC = E/(D+E) × r_e + D/(D+E) × r_d × (1 − t)

    所有比率均为百分点：tax_rate=21 表示 21%。
    """
    if debt is None or equity is None:
        return None
    total = debt + equity
    if total <= 0:
        return None
    t = tax_rate / 100.0
    r_e = capm_discount_rate(beta, risk_free, erp)
    weight_e = equity / total
    weight_d = debt / total
    value = weight_e * r_e + weight_d * cost_of_debt * (1 - t)
    return {
        "wacc": value,
        "cost_of_equity": r_e,
        "after_tax_cost_of_debt": cost_of_debt * (1 - t),
        "weight_equity": weight_e,
        "weight_debt": weight_d,
    }


# 按币种预填的无风险利率（%），可在设置中覆盖
DEFAULT_RISK_FREE = {
    "USD": 4.0,
    "CNY": 2.5,
    "HKD": 3.5,
    "EUR": 2.5,
    "JPY": 1.0,
    "GBP": 4.0,
}


def default_risk_free(currency: Optional[str]) -> float:
    if not currency:
        return DEFAULT_RISK_FREE["USD"]
    return DEFAULT_RISK_FREE.get(currency.upper(), DEFAULT_RISK_FREE["USD"])
