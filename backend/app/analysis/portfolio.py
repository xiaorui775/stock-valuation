"""投资组合汇总的纯计算（§5.9 FR-PORT-03 / 04 / 07）。

输入是已经取好的行情、汇率与持仓，输出市值、盈亏、权重与分布。无 I/O，
不做任何估算：汇率缺失的持仓不计入基础货币汇总，只按币种给出本币小计并提示。

约定：
- `fx_rate` 表示「1 单位持仓币种 = fx_rate 单位基础货币」，由服务层查汇率后传入。
- 金额单位为持仓币种 / 基础货币的原始单位（不是「亿」）。
- 百分数为百分点（10 表示 10%）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

CONCENTRATION_PCT = 30.0


@dataclass(frozen=True)
class HoldingRow:
    """一条持仓 + 取到的行情与汇率。缺失值为 None。"""

    ticker: str
    name: str
    market: str
    currency: Optional[str]
    quantity: float
    avg_cost: float
    price: Optional[float]
    previous_close: Optional[float]
    fx_rate: Optional[float]
    dcf_upside_pct: Optional[float] = None
    as_of: Optional[datetime] = None
    error: Optional[str] = None


def _pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100


def holding_metrics(row: HoldingRow) -> dict[str, Any]:
    """单条持仓的市值、成本、未实现盈亏与当日盈亏（基础货币 + 本币）。

    `converted` 为 False 表示缺少汇率，本币值仍然给出，基础货币值全部为 None。
    """
    local_value = None if row.price is None else row.quantity * row.price
    converted = local_value is not None and row.fx_rate is not None

    market_value = local_value * row.fx_rate if converted else None
    cost = row.quantity * row.avg_cost * row.fx_rate if row.fx_rate is not None else None
    unrealized = (
        market_value - cost
        if market_value is not None and cost is not None
        else None
    )
    day_pnl = (
        (row.price - row.previous_close) * row.quantity * row.fx_rate
        if converted and row.price is not None and row.previous_close is not None
        else None
    )
    return {
        "market_value": market_value,
        "market_value_local": local_value,
        "cost": cost,
        "unrealized_pnl": unrealized,
        "unrealized_pnl_pct": _pct(unrealized, cost),
        "day_pnl": day_pnl,
        "converted": converted,
    }


def summarize(
    rows: list[HoldingRow],
    base_currency: str,
    concentration_pct: float = CONCENTRATION_PCT,
) -> dict[str, Any]:
    """组合级汇总。

    - 空组合：各合计为 0（这是真实的「没有持仓」，不是缺失数据）。
    - 有持仓但没有一条能换算：合计为 None，并说明缺什么，绝不把缺失当 0。
    """
    metrics = [holding_metrics(row) for row in rows]
    converted = [m for m in metrics if m["converted"]]

    totals: dict[str, Any] = {
        "total_market_value": None,
        "total_cost": None,
        "unrealized_pnl": None,
        "unrealized_pnl_pct": None,
        "day_pnl": None,
        "day_pnl_pct": None,
    }
    if not rows:
        totals = {
            "total_market_value": 0.0,
            "total_cost": 0.0,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": None,
            "day_pnl": 0.0,
            "day_pnl_pct": None,
        }
    elif converted:
        total_value = sum(m["market_value"] for m in converted)
        total_cost = sum(m["cost"] for m in converted if m["cost"] is not None)
        unrealized = total_value - total_cost
        day_values = [m["day_pnl"] for m in converted if m["day_pnl"] is not None]
        day_pnl = sum(day_values) if day_values else None
        previous_value = total_value - day_pnl if day_pnl is not None else None
        totals = {
            "total_market_value": total_value,
            "total_cost": total_cost,
            "unrealized_pnl": unrealized,
            "unrealized_pnl_pct": _pct(unrealized, total_cost),
            "day_pnl": day_pnl,
            "day_pnl_pct": _pct(day_pnl, previous_value),
        }

    total_value = totals["total_market_value"]

    # 权重：只对能换算的持仓计算，合计恰好 100%（缺失汇率的持仓不参与）
    weights: dict[int, Optional[float]] = {}
    for index, metric in enumerate(metrics):
        weights[index] = (
            _pct(metric["market_value"], total_value)
            if metric["converted"] and total_value
            else None
        )

    # 未换算：按币种给出本币小计，供前端分组展示
    unconverted_groups: dict[str, dict[str, Any]] = {}
    unpriced = 0
    for row, metric in zip(rows, metrics, strict=True):
        if metric["converted"]:
            continue
        key = row.currency or "UNKNOWN"
        group = unconverted_groups.setdefault(
            key,
            {"currency": key, "count": 0, "priced_count": 0, "market_value_local": 0.0},
        )
        group["count"] += 1
        if metric["market_value_local"] is None:
            unpriced += 1
        else:
            group["market_value_local"] += metric["market_value_local"]
            group["priced_count"] += 1
    for group in unconverted_groups.values():
        if group["priced_count"] == 0:
            group["market_value_local"] = None

    # 市场分布（按可换算市值）
    market_groups: dict[str, float] = {}
    for row, metric in zip(rows, metrics, strict=True):
        if not metric["converted"]:
            continue
        market_groups[row.market or "UNKNOWN"] = (
            market_groups.get(row.market or "UNKNOWN", 0.0) + metric["market_value"]
        )
    distribution = [
        {
            "market": market,
            "market_value": value,
            "weight_pct": _pct(value, total_value),
        }
        for market, value in sorted(market_groups.items(), key=lambda kv: -kv[1])
    ]

    # 组合加权估值上行空间：按市值加权，只统计有 DCF 上行空间的持仓
    upside_rows = [
        (row, metric)
        for row, metric in zip(rows, metrics, strict=True)
        if metric["converted"] and row.dcf_upside_pct is not None
    ]
    upside_value = sum(metric["market_value"] for _row, metric in upside_rows)
    weighted_upside = (
        sum(row.dcf_upside_pct * metric["market_value"] for row, metric in upside_rows)
        / upside_value
        if upside_value
        else None
    )
    upside_coverage = _pct(upside_value, total_value) if total_value else None

    concentration = [
        {"ticker": row.ticker, "name": row.name, "weight_pct": weights[index]}
        for index, row in enumerate(rows)
        if weights[index] is not None and weights[index] > concentration_pct
    ]

    warnings: list[str] = []
    fx_groups = [
        group
        for group in unconverted_groups.values()
        if group["market_value_local"] is not None
    ]
    if fx_groups:
        parts = "、".join(
            f"{group['currency']}（{group['count']} 条）" for group in fx_groups
        )
        warnings.append(
            f"缺少 {parts} 对 {base_currency} 的汇率，这些持仓未计入基础货币汇总，"
            "按币种单独列出，未做估算转换。"
        )
    if unpriced:
        warnings.append(f"{unpriced} 条持仓缺少可用行情，未计入任何金额统计。")
    if rows and not converted:
        warnings.append("所有持仓都缺少可用的行情或汇率，无法计算组合汇总。")
    if weighted_upside is None and rows:
        warnings.append("没有持仓同时具备行情与 DCF 估值，组合加权上行空间不可用。")
    for item in concentration:
        warnings.append(
            f"{item['ticker']} 权重 {item['weight_pct']:.1f}% 超过 {concentration_pct:.0f}%，"
            "单一持仓集中度较高（事实提示，不构成建议）。"
        )

    return {
        **totals,
        "base_currency": base_currency,
        "unconverted": list(unconverted_groups.values()),
        "distribution": distribution,
        "weighted_upside_pct": weighted_upside,
        "upside_coverage_pct": upside_coverage,
        "concentration": concentration,
        "warnings": warnings,
        "rows": [
            {
                "ticker": row.ticker,
                "name": row.name,
                "market": row.market,
                "currency": row.currency,
                "quantity": row.quantity,
                "avg_cost": row.avg_cost,
                "price": row.price,
                "previous_close": row.previous_close,
                "fx_rate": row.fx_rate,
                "dcf_upside_pct": row.dcf_upside_pct,
                "as_of": row.as_of,
                "error": row.error,
                **metric,
                "weight_pct": weights[index],
            }
            for index, (row, metric) in enumerate(zip(rows, metrics, strict=True))
        ],
    }
