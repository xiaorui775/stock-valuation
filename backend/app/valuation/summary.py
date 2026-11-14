"""加权综合估值：用户选择参与方法并给出权重（FR-VAL-13）。"""
from __future__ import annotations

from typing import Optional

#: 权重合计允许的误差（百分点）。前端保留 1 位小数，避免 33.3×3 这类舍入误差被拒。
WEIGHT_TOLERANCE = 0.05

#: 「低估 / 高估」判定阈值（百分点）。
BAND_THRESHOLD = 15.0


def band_for(
    diff_pct: Optional[float], threshold: float = BAND_THRESHOLD
) -> Optional[str]:
    """按相对现价的偏离幅度给出模型判定。"""
    if diff_pct is None:
        return None
    if diff_pct > threshold:
        return "低估"
    if diff_pct < -threshold:
        return "高估"
    return "合理"


def combine(
    entries: list[tuple[str, float, float]],
    price: Optional[float],
    threshold: float = BAND_THRESHOLD,
) -> Optional[dict]:
    """按权重合成每股价值。

    `entries` 为 `(方法名, 每股价值, 权重百分点)`。权重合计不为 100 或没有参与方法时返回 None，
    由调用方给出错误说明——不做静默归一化，否则用户看到的权重和实际生效的不一致。
    """
    if not entries:
        return None
    total_weight = sum(weight for _, _, weight in entries)
    if abs(total_weight - 100.0) > WEIGHT_TOLERANCE:
        return None
    if any(weight < 0 for _, _, weight in entries):
        return None

    weighted = sum(value * weight for _, value, weight in entries) / 100.0
    diff_pct = ((weighted - price) / price * 100) if price else None
    methods = [
        {
            "name": name,
            "value": value,
            "weight": weight,
            "contribution": value * weight / 100.0,
        }
        for name, value, weight in entries
    ]
    return {
        "average_value": weighted,
        "methods_used": len(entries),
        "methods": methods,
        "vs_price_pct": diff_pct,
        "band": band_for(diff_pct, threshold),
        "total_weight": total_weight,
    }
