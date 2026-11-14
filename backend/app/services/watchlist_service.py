"""自选股服务：分组与条目的增删改、排序（FR-WATCH-01 / 02）。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.models.watchlist import WatchlistGroup, WatchlistItem
from app.providers.base import detect_market
from app.repositories.watchlist_repo import WatchlistRepository
from app.services.market_calendar import days_until
from app.services.market_service import MarketService
from app.services.valuation_service import ValuationService

DEFAULT_GROUP = "我的自选"
QUOTE_WORKERS = 8


class WatchlistService:
    def __init__(self, db: OrmSession, market: MarketService | None = None) -> None:
        self.db = db
        self.repo = WatchlistRepository(db)
        self.market = market or MarketService()

    # ---- 分组 ----
    def list(self, user_id: int) -> list[dict[str, Any]]:
        """列出全部分组；首次访问自动创建一个默认分组。"""
        groups = self.repo.list_groups(user_id)
        if not groups:
            groups = [self._create_default_group(user_id)]
        return [self._serialize_group(group) for group in groups]

    def create_group(self, user_id: int, name: str) -> dict[str, Any]:
        name = self._clean_name(name)
        if self.repo.get_group_by_name(user_id, name) is not None:
            raise AppError(ErrorCode.CONFLICT, f"分组「{name}」已存在", 409)
        group = self.repo.add_group(
            WatchlistGroup(
                user_id=user_id, name=name, sort_order=self.repo.next_group_order(user_id)
            )
        )
        self.db.commit()
        self.db.refresh(group)
        return self._serialize_group(group)

    def rename_group(self, user_id: int, group_id: int, name: str) -> dict[str, Any]:
        group = self._owned_group(user_id, group_id)
        cleaned = self._clean_name(name)
        if cleaned != group.name:
            if self.repo.get_group_by_name(user_id, cleaned) is not None:
                raise AppError(ErrorCode.CONFLICT, f"分组「{cleaned}」已存在", 409)
            group.name = cleaned
        self.db.commit()
        self.db.refresh(group)
        return self._serialize_group(group)

    def delete_group(self, user_id: int, group_id: int) -> dict[str, Any]:
        group = self._owned_group(user_id, group_id)
        self.repo.delete_group(group)
        self.db.commit()
        return {"id": group_id, "deleted": True}

    def reorder_groups(self, user_id: int, group_ids: list[int]) -> list[dict[str, Any]]:
        groups = {group.id: group for group in self.repo.list_groups(user_id)}
        for index, group_id in enumerate(group_ids):
            if group_id in groups:
                groups[group_id].sort_order = index
        self.db.commit()
        return [self._serialize_group(group) for group in self.repo.list_groups(user_id)]

    # ---- 条目 ----
    def add_item(self, user_id: int, group_id: int, ticker: str) -> dict[str, Any]:
        group = self._owned_group(user_id, group_id)
        symbol = normalize_ticker(ticker)
        if not symbol:
            raise AppError(ErrorCode.UNPROCESSABLE, "请填写股票代码", 422)
        if self.repo.get_item(group.id, symbol) is not None:
            raise AppError(
                ErrorCode.CONFLICT, f"{symbol} 已在「{group.name}」中", 409
            )
        # 校验代码有效：无效代码由 provider 抛 TickerNotFound（404）
        quote, _meta = self.market.get_quote(symbol)
        item = self.repo.add_item(
            WatchlistItem(
                group_id=group.id,
                ticker=quote.ticker,
                name=quote.name,
                market=quote.market.value,
                currency=quote.currency,
                sort_order=self.repo.next_item_order(group.id),
            )
        )
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_item(item)

    def add_items(
        self, user_id: int, group_id: int, tickers: list[str]
    ) -> dict[str, Any]:
        """批量添加：逐个校验，失败项不阻断其余条目。"""
        added: list[dict[str, Any]] = []
        failed: list[dict[str, str]] = []
        for raw in tickers:
            try:
                added.append(self.add_item(user_id, group_id, raw))
            except AppError as exc:
                failed.append(
                    {"ticker": normalize_ticker(raw) or raw, "reason": exc.message}
                )
        return {"added": added, "failed": failed}

    def remove_item(self, user_id: int, group_id: int, item_id: int) -> dict[str, Any]:
        group = self._owned_group(user_id, group_id)
        item = self.repo.get_item_by_id(group.id, item_id)
        if item is None:
            raise AppError(ErrorCode.NOT_FOUND, "条目不存在", 404)
        self.repo.delete_item(item)
        self.db.commit()
        return {"id": item_id, "deleted": True}

    def reorder_items(
        self, user_id: int, group_id: int, item_ids: list[int]
    ) -> list[dict[str, Any]]:
        group = self._owned_group(user_id, group_id)
        items = {item.id: item for item in self.repo.list_items(group.id)}
        for index, item_id in enumerate(item_ids):
            if item_id in items:
                items[item_id].sort_order = index
        self.db.commit()
        return [self._serialize_item(item) for item in self.repo.list_items(group.id)]

    # ---- 批量行情 ----
    def quotes(self, user_id: int, group_id: int) -> dict[str, Any]:
        """一次取一个分组的全部行情与估值列（FR-WATCH-03 / 05）。

        并发受限（8 线程）；单只失败只影响该行，返回 `error` 由前端保留上次数据。
        """
        group = self._owned_group(user_id, group_id)
        items = self.repo.list_items(group.id)
        rows: list[dict[str, Any]] = []
        if items:
            with ThreadPoolExecutor(max_workers=QUOTE_WORKERS) as pool:
                rows = list(pool.map(self._quote_row, items))
        return {
            "group_id": group.id,
            "items": rows,
            "refreshed_at": datetime.now(UTC),
        }

    def _quote_row(self, item: WatchlistItem) -> dict[str, Any]:
        base: dict[str, Any] = {
            "ticker": item.ticker,
            "name": item.name,
            "market": item.market,
            "currency": item.currency,
            "price": None,
            "change_pct": None,
            "market_cap": None,
            "pe_ttm": None,
            "forward_pe": None,
            "dividend_yield": None,
            "fcf_yield": None,
            "dcf_upside_pct": None,
            "earnings_date": None,
            "days_until_earnings": None,
            "earnings_source": None,
            "as_of": None,
            "stale": False,
            "error": None,
        }
        try:
            quote, meta = self.market.get_quote(item.ticker)
        except AppError as exc:
            return {**base, "error": exc.message}

        row: dict[str, Any] = {
            **base,
            "name": quote.name,
            "market": quote.market.value,
            "currency": quote.currency,
            "price": quote.price,
            "change_pct": quote.change_pct,
            "market_cap": quote.market_cap,
            "pe_ttm": quote.pe_ttm,
            "forward_pe": quote.forward_pe,
            "dividend_yield": quote.dividend_yield,
            "as_of": quote.as_of,
            "stale": bool(meta.get("stale")),
        }

        # 财报日作为独立信息列；数据源没有日历时留空，不影响行情
        try:
            info, calendar_meta = self.market.get_calendar(item.ticker)
        except AppError:
            info, calendar_meta = None, {}
        if info is not None and info.earnings_date is not None:
            remaining = days_until(info.earnings_date, detect_market(item.ticker))
            if remaining is not None:
                row["earnings_date"] = info.earnings_date
                row["days_until_earnings"] = remaining
                row["earnings_source"] = calendar_meta.get("source")

        # 估值列需要财报；财报缺失时留空，不影响其余行情列
        try:
            financials, _ = self.market.get_financials(item.ticker)
            valuation = ValuationService(quote, financials).build()
            dcf = valuation.get("dcf") or {}
            row["dcf_upside_pct"] = dcf.get("upside_pct")
            row["fcf_yield"] = next(
                (
                    m["value"]
                    for m in valuation.get("multiples", [])
                    if m["name"] == "FCF Yield"
                ),
                None,
            )
        except AppError:
            pass
        return row

    # ------------------------------------------------------------------
    def _create_default_group(self, user_id: int) -> WatchlistGroup:
        group = self.repo.add_group(
            WatchlistGroup(user_id=user_id, name=DEFAULT_GROUP, sort_order=0)
        )
        self.db.commit()
        self.db.refresh(group)
        return group

    def _owned_group(self, user_id: int, group_id: int) -> WatchlistGroup:
        group = self.repo.get_group(user_id, group_id)
        if group is None:
            raise AppError(ErrorCode.NOT_FOUND, "分组不存在", 404)
        return group

    def _serialize_group(self, group: WatchlistGroup) -> dict[str, Any]:
        return {
            "id": group.id,
            "name": group.name,
            "sort_order": group.sort_order,
            "items": [self._serialize_item(item) for item in self.repo.list_items(group.id)],
        }

    @staticmethod
    def _serialize_item(item: WatchlistItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "ticker": item.ticker,
            "name": item.name,
            "market": item.market,
            "currency": item.currency,
            "sort_order": item.sort_order,
        }

    @staticmethod
    def _clean_name(name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise AppError(ErrorCode.UNPROCESSABLE, "分组名称不能为空", 422)
        return cleaned
