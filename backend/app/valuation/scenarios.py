"""情景分析：Bear / Base / Bull 三套假设与加权期望。"""
from __future__ import annotations

from typing import Optional

from app.valuation.dcf import dcf_value

SCENARIO_NAMES = ("bear", "base", "bull")


def run_scenario(
    base_fcf: Optional[float],
    growth_pct: float,
    terminal_growth_pct: float,
    discount_pct: float,
    total_debt: Optional[float],
    total_cash: Optional[float],
    shares: Optional[float],
    years1: int = 5,
) -> Optional[dict]:
    res = dcf_value(
        base_fcf, growth_pct, years1, terminal_growth_pct, discount_pct,
        total_debt, total_cash, shares,
    )
    if res is None:
        return None
    return {
        "per_share": res["per_share"],
        "enterprise_value": res["enterprise_value"],
        "equity_value": res["equity_value"],
        "pv_terminal_ratio": res["pv_terminal_ratio"],
    }


def build_scenarios(
    base_fcf: Optional[float],
    scenarios: list[dict],
    total_debt: Optional[float],
    total_cash: Optional[float],
    shares: Optional[float],
    price: Optional[float],
    years1: int = 5,
) -> dict:
    """执行多情景并计算加权期望价值。

    scenarios 每项：{name, growth, terminal, discount, probability}。
    概率之和不为 100 时返回 error，不做静默归一化。
    """
    total_probability = sum(float(s.get("probability") or 0) for s in scenarios)
    if abs(total_probability - 100.0) > 1e-6:
        return {
            "scenarios": [],
            "weighted": None,
            "error": f"情景概率之和为 {total_probability:g}%，必须等于 100%",
        }

    results = []
    weighted_sum = 0.0
    used = 0.0
    for s in scenarios:
        value = run_scenario(
            base_fcf,
            float(s.get("growth", 10.0)),
            float(s.get("terminal", 2.5)),
            float(s.get("discount", 9.0)),
            total_debt,
            total_cash,
            shares,
            years1=years1,
        )
        probability = float(s.get("probability") or 0)
        if value is None:
            results.append(
                {
                    "name": s.get("name", "?"),
                    "growth": s.get("growth"),
                    "terminal": s.get("terminal"),
                    "discount": s.get("discount"),
                    "probability": probability,
                    "per_share": None,
                    "upside_pct": None,
                    "error": "条件不成立，无法计算",
                }
            )
            continue
        weighted_sum += value["per_share"] * probability
        used += probability
        results.append(
            {
                "name": s.get("name", "?"),
                "growth": s.get("growth"),
                "terminal": s.get("terminal"),
                "discount": s.get("discount"),
                "probability": probability,
                "per_share": value["per_share"],
                "enterprise_value": value["enterprise_value"],
                "equity_value": value["equity_value"],
                "upside_pct": (
                    (value["per_share"] - price) / price * 100 if price else None
                ),
            }
        )

    weighted = (weighted_sum / used) if used > 0 else None
    return {
        "scenarios": results,
        "weighted": weighted,
        "weighted_upside_pct": (
            (weighted - price) / price * 100 if weighted is not None and price else None
        ),
        "error": None,
    }
