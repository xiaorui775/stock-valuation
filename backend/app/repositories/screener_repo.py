"""预设指数成分与筛选预设的数据访问。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from app.models.screener import IndexConstituent, ScreenerPreset


class IndexRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    def list(self, index_key: str) -> list[IndexConstituent]:
        return list(
            self.db.scalars(
                select(IndexConstituent)
                .where(IndexConstituent.index_key == index_key)
                .order_by(IndexConstituent.sort_order, IndexConstituent.id)
            )
        )

    def replace(
        self, index_key: str, rows: list[tuple[str, str]], source: str
    ) -> list[IndexConstituent]:
        """整表替换某指数的成分，保证与数据源一致（不做增量猜测）。"""
        self.db.execute(
            delete(IndexConstituent).where(IndexConstituent.index_key == index_key)
        )
        for order, (ticker, name) in enumerate(rows):
            self.db.add(
                IndexConstituent(
                    index_key=index_key,
                    ticker=ticker,
                    name=name,
                    sort_order=order,
                    source=source,
                )
            )
        self.db.flush()
        return self.list(index_key)


class ScreenerPresetRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    def list(self, user_id: int) -> list[ScreenerPreset]:
        return list(
            self.db.scalars(
                select(ScreenerPreset)
                .where(ScreenerPreset.user_id == user_id)
                .order_by(ScreenerPreset.id)
            )
        )

    def get(self, user_id: int, preset_id: int) -> Optional[ScreenerPreset]:
        return self.db.scalar(
            select(ScreenerPreset).where(
                ScreenerPreset.id == preset_id, ScreenerPreset.user_id == user_id
            )
        )

    def get_by_name(self, user_id: int, name: str) -> Optional[ScreenerPreset]:
        return self.db.scalar(
            select(ScreenerPreset).where(
                ScreenerPreset.user_id == user_id, ScreenerPreset.name == name
            )
        )

    def add(self, preset: ScreenerPreset) -> ScreenerPreset:
        self.db.add(preset)
        self.db.flush()
        return preset

    def delete(self, preset: ScreenerPreset) -> None:
        self.db.delete(preset)
        self.db.flush()
