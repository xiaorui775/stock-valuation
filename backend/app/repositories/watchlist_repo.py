"""自选股数据访问。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models.watchlist import WatchlistGroup, WatchlistItem


class WatchlistRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    # ---- 分组 ----
    def list_groups(self, user_id: int) -> list[WatchlistGroup]:
        return list(
            self.db.scalars(
                select(WatchlistGroup)
                .where(WatchlistGroup.user_id == user_id)
                .order_by(WatchlistGroup.sort_order, WatchlistGroup.id)
            )
        )

    def get_group(self, user_id: int, group_id: int) -> Optional[WatchlistGroup]:
        return self.db.scalar(
            select(WatchlistGroup).where(
                WatchlistGroup.id == group_id, WatchlistGroup.user_id == user_id
            )
        )

    def get_group_by_name(self, user_id: int, name: str) -> Optional[WatchlistGroup]:
        return self.db.scalar(
            select(WatchlistGroup).where(
                WatchlistGroup.user_id == user_id, WatchlistGroup.name == name
            )
        )

    def add_group(self, group: WatchlistGroup) -> WatchlistGroup:
        self.db.add(group)
        self.db.flush()
        return group

    def delete_group(self, group: WatchlistGroup) -> None:
        self.db.delete(group)
        self.db.flush()

    def next_group_order(self, user_id: int) -> int:
        current = self.db.scalar(
            select(func.max(WatchlistGroup.sort_order)).where(
                WatchlistGroup.user_id == user_id
            )
        )
        return 0 if current is None else current + 1

    # ---- 条目 ----
    def list_items(self, group_id: int) -> list[WatchlistItem]:
        return list(
            self.db.scalars(
                select(WatchlistItem)
                .where(WatchlistItem.group_id == group_id)
                .order_by(WatchlistItem.sort_order, WatchlistItem.id)
            )
        )

    def get_item(self, group_id: int, ticker: str) -> Optional[WatchlistItem]:
        return self.db.scalar(
            select(WatchlistItem).where(
                WatchlistItem.group_id == group_id, WatchlistItem.ticker == ticker
            )
        )

    def get_item_by_id(self, group_id: int, item_id: int) -> Optional[WatchlistItem]:
        return self.db.scalar(
            select(WatchlistItem).where(
                WatchlistItem.id == item_id, WatchlistItem.group_id == group_id
            )
        )

    def add_item(self, item: WatchlistItem) -> WatchlistItem:
        self.db.add(item)
        self.db.flush()
        return item

    def delete_item(self, item: WatchlistItem) -> None:
        self.db.delete(item)
        self.db.flush()

    def next_item_order(self, group_id: int) -> int:
        current = self.db.scalar(
            select(func.max(WatchlistItem.sort_order)).where(
                WatchlistItem.group_id == group_id
            )
        )
        return 0 if current is None else current + 1
