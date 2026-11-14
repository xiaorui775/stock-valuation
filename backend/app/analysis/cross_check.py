"""A 股数据交叉校验（FR-DATA-04）。

akshare 之外还有一条独立来源：新浪行情扩展字段里的「营业收入 TTM」。
两者口径不同（年报 vs TTM），直接比较必然有差异；这里比较的是
「年报营收 × TTM/年报比」无法成立，因此改为校验 TTM 营收与最近年报营收
的比例是否在合理区间（0.5–2.0），超出说明某一侧解析有误。

差异 > 2% 时在响应 meta 附 `cross_check` 区块，UI 据此标记
「数据源存在差异」并展示两个值。纯计算，不做网络请求。
"""
from __future__ import annotations

from typing import Any

# TTM 与年报的比例合理区间；超出视为数据异常而非口径差异
TTM_RATIO_MIN = 0.5
TTM_RATIO_MAX = 2.0

# 年报口径下两侧的差异容忍度（FR-DATA-04：> 2% 标记）
DIFF_PCT_THRESHOLD = 2.0


def cross_check_revenue(
    annual_revenue: float | None,
    ttm_revenue: float | None,
) -> dict[str, Any] | None:
    """营业收入一致性检查。

    - 两侧都缺失或任一缺失：返回 None（无法校验，不是异常）。
    - 年报 vs TTM：比例在合理区间内视为正常（口径不同），只报告参考值；
      超出区间视为「数据源存在差异」。
    """
    if annual_revenue is None or ttm_revenue is None or annual_revenue == 0:
        return None

    ratio = ttm_revenue / annual_revenue
    in_range = TTM_RATIO_MIN <= ratio <= TTM_RATIO_MAX
    # 差异按相对「年报」计算，单位百分点
    diff_pct = (ttm_revenue - annual_revenue) / abs(annual_revenue) * 100

    return {
        "field": "revenue",
        "values": {
            "annual": annual_revenue,
            "ttm": ttm_revenue,
        },
        "ratio": ratio,
        "diff_pct": diff_pct,
        # 口径不同（TTM vs 年报）时 difference 是预期行为，不算异常；
        # 比例越界才是真正需要标记的「数据源存在差异」。
        "conflict": not in_range,
        "note": (
            "TTM 营收与最近年报口径不同，比例在合理区间内。"
            if in_range
            else "数据源存在差异：TTM 营收与最近年报比例异常，请以年报为准。"
        ),
    }


def cross_check_annual(
    a: float | None,
    b: float | None,
    field: str,
    source_a: str,
    source_b: str,
) -> dict[str, Any] | None:
    """两个数据源同一字段的年报一致性检查（差异 > 2% 标记）。"""
    if a is None or b is None:
        return None
    base = min(abs(a), abs(b))
    if base == 0:
        return None
    diff_pct = abs(a - b) / base * 100
    return {
        "field": field,
        "values": {source_a: a, source_b: b},
        "diff_pct": diff_pct,
        "conflict": diff_pct > DIFF_PCT_THRESHOLD,
        "note": (
            f"数据源存在差异：{field} 两侧相差 {diff_pct:.2f}%。"
            if diff_pct > DIFF_PCT_THRESHOLD
            else f"{field} 两侧一致（差异 {diff_pct:.2f}%）。"
        ),
    }
