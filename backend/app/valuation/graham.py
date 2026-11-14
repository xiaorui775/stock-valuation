"""Graham 数字。"""
from __future__ import annotations

from typing import Optional


def graham_number(
    eps: Optional[float], book_value_per_share: Optional[float]
) -> Optional[float]:
    """Graham 数字 = √(22.5 × EPS × 每股净资产)。"""
    if eps is None or book_value_per_share is None:
        return None
    if eps <= 0 or book_value_per_share <= 0:
        return None
    return (22.5 * eps * book_value_per_share) ** 0.5
