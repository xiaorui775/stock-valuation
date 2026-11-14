"""估值预设的数据访问。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models.preset import ValuationPreset


class PresetRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    def list_for(self, user_id: int, ticker: str) -> list[ValuationPreset]:
        return list(
            self.db.scalars(
                select(ValuationPreset)
                .where(
                    ValuationPreset.user_id == user_id,
                    ValuationPreset.ticker == ticker,
                )
                .order_by(ValuationPreset.updated_at.desc(), ValuationPreset.id.desc())
            )
        )

    def get(self, user_id: int, preset_id: int) -> Optional[ValuationPreset]:
        """按用户过滤，避免越权读取他人的预设。"""
        return self.db.scalar(
            select(ValuationPreset).where(
                ValuationPreset.id == preset_id,
                ValuationPreset.user_id == user_id,
            )
        )

    def get_by_name(
        self, user_id: int, ticker: str, name: str
    ) -> Optional[ValuationPreset]:
        return self.db.scalar(
            select(ValuationPreset).where(
                ValuationPreset.user_id == user_id,
                ValuationPreset.ticker == ticker,
                ValuationPreset.name == name,
            )
        )

    def by_ids(
        self, user_id: int, preset_ids: list[int]
    ) -> dict[int, ValuationPreset]:
        """批量取预设，供笔记列表附带预设名称（避免逐条查询）。"""
        if not preset_ids:
            return {}
        rows = self.db.scalars(
            select(ValuationPreset).where(
                ValuationPreset.user_id == user_id,
                ValuationPreset.id.in_(preset_ids),
            )
        )
        return {preset.id: preset for preset in rows}

    def add(self, preset: ValuationPreset) -> ValuationPreset:
        self.db.add(preset)
        self.db.flush()
        return preset

    def delete(self, preset: ValuationPreset) -> None:
        self.db.delete(preset)
        self.db.flush()
