"""常用对比组合的数据访问（FR-RESEARCH-06）。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models.compare_preset import ComparePreset


class ComparePresetRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    def list_for(self, user_id: int) -> list[ComparePreset]:
        return list(
            self.db.scalars(
                select(ComparePreset)
                .where(ComparePreset.user_id == user_id)
                .order_by(ComparePreset.updated_at.desc(), ComparePreset.id.desc())
            )
        )

    def get(self, user_id: int, preset_id: int) -> Optional[ComparePreset]:
        return self.db.scalar(
            select(ComparePreset).where(
                ComparePreset.id == preset_id,
                ComparePreset.user_id == user_id,
            )
        )

    def get_by_name(self, user_id: int, name: str) -> Optional[ComparePreset]:
        return self.db.scalar(
            select(ComparePreset).where(
                ComparePreset.user_id == user_id,
                ComparePreset.name == name,
            )
        )

    def add(self, preset: ComparePreset) -> ComparePreset:
        self.db.add(preset)
        self.db.flush()
        return preset

    def delete(self, preset: ComparePreset) -> None:
        self.db.delete(preset)
        self.db.flush()
