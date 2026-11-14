"""筛选器服务：股票池解析、并发取数、条件过滤、排序与分页（§5.11）。

规模控制（FR-SCR-06）：股票池上限 500，并发 4；命中缓存由 MarketService 处理。
部分标的取数失败不中断整体，结果里给出成功/失败数量与原因（FR-SCR-05）。
"""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.analysis.screener import Filter, paginate, passes, sort_rows
from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.repositories.watchlist_repo import WatchlistRepository
from app.services.index_service import IndexService
from app.services.market_service import MarketService
from app.services.quote_metrics import fetch_metrics

POOL_LIMIT = 500
SCREEN_WORKERS = 4
PER_TICKER_SECONDS = 1.5
ESTIMATE_NOTE = (
    "预计耗时按每只 1.5 秒、并发 4 的冷缓存粗略估计，缓存命中会明显更快。"
)

ROW_FIELDS: tuple[str, ...] = (
    "ticker",
    "name",
    "market",
    "currency",
    "price",
    "market_cap",
    "pe_ttm",
    "forward_pe",
    "peg",
    "price_to_book",
    "price_to_sales",
    "ev_ebitda",
    "dividend_yield",
    "revenue_growth",
    "fcf_yield",
    "dcf_upside_pct",
    "beta",
    "as_of",
)


class ScreenerService:
    def __init__(self, db: OrmSession, market: MarketService | None = None) -> None:
        self.db = db
        self.market = market or MarketService()
        self.watchlists = WatchlistRepository(db)

    def run(
        self,
        user_id: int,
        *,
        pool_kind: str,
        tickers: list[str],
        watchlist_id: int | None,
        index_key: str | None,
        market_filter: list[str] | None,
        filters: list[dict[str, Any]],
        sort_key: str | None,
        sort_desc: bool,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        symbols = self._pool(user_id, pool_kind, tickers, watchlist_id, index_key)
        rules = [
            Filter(
                metric=item["metric"],
                minimum=item.get("min"),
                maximum=item.get("max"),
            )
            for item in filters
        ]

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=SCREEN_WORKERS) as pool:
            results = list(pool.map(self._row, symbols))
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        rows: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        for item in results:
            if item["error"]:
                failures.append({"ticker": item["ticker"], "reason": item["error"]})
                continue
            if market_filter and item["market"] not in market_filter:
                continue
            rows.append(item)

        matched = [row for row in rows if passes(row, rules)]
        ordered = sort_rows(matched, sort_key, sort_desc)

        return {
            "as_of": datetime.now(UTC),
            "page": page,
            "page_size": page_size,
            "total": len(ordered),
            "requested": len(symbols),
            "succeeded": len(rows),
            "failed": len(failures),
            "failures": failures,
            "rows": [
                {field: row.get(field) for field in ROW_FIELDS}
                for row in paginate(ordered, page, page_size)
            ],
            "elapsed_ms": elapsed_ms,
            "estimate_seconds": math.ceil(len(symbols) / SCREEN_WORKERS) * PER_TICKER_SECONDS,
            "note": ESTIMATE_NOTE,
        }

    # ------------------------------------------------------------------
    def _pool(
        self,
        user_id: int,
        kind: str,
        tickers: list[str],
        watchlist_id: int | None,
        index_key: str | None,
    ) -> list[str]:
        if kind == "index":
            if not index_key:
                raise AppError(ErrorCode.UNPROCESSABLE, "请选择预设指数", 422)
            raw = IndexService(self.db, self.market).tickers(index_key)
        elif kind == "watchlist":
            if watchlist_id is None:
                raise AppError(ErrorCode.UNPROCESSABLE, "请选择自选分组", 422)
            group = self.watchlists.get_group(user_id, watchlist_id)
            if group is None:
                raise AppError(ErrorCode.NOT_FOUND, "分组不存在", 404)
            raw = [item.ticker for item in self.watchlists.list_items(group.id)]
        else:
            raw = tickers

        symbols: list[str] = []
        for value in raw:
            symbol = normalize_ticker(value)
            if symbol and symbol not in symbols:
                symbols.append(symbol)
        if not symbols:
            raise AppError(ErrorCode.UNPROCESSABLE, "股票池为空，请先添加代码", 422)
        if len(symbols) > POOL_LIMIT:
            raise AppError(
                ErrorCode.UNPROCESSABLE, f"股票池最多 {POOL_LIMIT} 只", 422
            )
        return symbols

    def _row(self, symbol: str) -> dict[str, Any]:
        try:
            metrics = fetch_metrics(self.market, symbol)
        except AppError as exc:
            return {
                "ticker": symbol,
                "name": symbol,
                "market": "UNKNOWN",
                "currency": None,
                "price": None,
                "error": exc.message,
            }
        return {**metrics, "error": None}
