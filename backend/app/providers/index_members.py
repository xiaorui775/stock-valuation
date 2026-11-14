"""预设指数的内置成分股快照（§5.11 FR-SCR-01 / Q11）。

这些是各指数的常见成分股快照，用于离线与演示环境。指数会定期调整成分，
所以接口与 UI 都必须带上 `updated_at` 与来源，不能把它当成实时成分。
真实环境下的刷新由数据源完成（akshare 接入见 M2-15）。
"""
from __future__ import annotations

from datetime import date

SNAPSHOT_DATE = date(2026, 6, 30)
SNAPSHOT_SOURCE = "内置快照"

INDEX_LABELS: dict[str, str] = {
    "sp500": "S&P 500",
    "csi300": "沪深 300",
    "hsi": "恒生指数",
}

INDEX_SNAPSHOTS: dict[str, tuple[str, ...]] = {
    "sp500": (
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "TSLA",
        "GOOGL",
        "META",
        "BRK-B",
        "JPM",
        "V",
        "UNH",
        "XOM",
        "JNJ",
        "WMT",
        "MA",
        "PG",
        "HD",
        "COST",
        "ORCL",
        "AVGO",
    ),
    "csi300": (
        "600519.SS",
        "000001.SZ",
        "601318.SS",
        "600036.SS",
        "000858.SZ",
        "601888.SS",
        "002594.SZ",
        "600900.SS",
        "601166.SS",
        "000333.SZ",
        "600276.SS",
        "601899.SS",
        "600030.SS",
        "000651.SZ",
        "601012.SS",
    ),
    "hsi": (
        "0700.HK",
        "9988.HK",
        "0939.HK",
        "1299.HK",
        "0005.HK",
        "3690.HK",
        "0388.HK",
        "2318.HK",
        "1810.HK",
        "0883.HK",
        "9618.HK",
        "2020.HK",
        "0016.HK",
        "0001.HK",
        "2382.HK",
    ),
}
