"""估值预设服务：保存、加载、更新、删除（FR-VAL-07）。"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.models.preset import ValuationPreset
from app.repositories.preset_repo import PresetRepository
from app.schemas.preset import PresetAssumptions


class PresetService:
    def __init__(self, db: OrmSession) -> None:
        self.db = db
        self.repo = PresetRepository(db)

    # ------------------------------------------------------------------
    def list(self, user_id: int, ticker: str) -> list[dict[str, Any]]:
        return [
            self._serialize(preset)
            for preset in self.repo.list_for(user_id, normalize_ticker(ticker))
        ]

    def create(
        self, user_id: int, ticker: str, name: str, assumptions: PresetAssumptions
    ) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        name = (name or "").strip()
        if not name:
            raise AppError(ErrorCode.UNPROCESSABLE, "预设名称不能为空", 422)
        if self.repo.get_by_name(user_id, ticker, name) is not None:
            raise AppError(ErrorCode.CONFLICT, f"预设「{name}」已存在", 409)
        preset = self.repo.add(
            ValuationPreset(
                user_id=user_id,
                ticker=ticker,
                name=name,
                assumptions_json=assumptions.model_dump_json(),
            )
        )
        self.db.commit()
        self.db.refresh(preset)
        return self._serialize(preset)

    def update(
        self,
        user_id: int,
        ticker: str,
        preset_id: int,
        name: Optional[str] = None,
        assumptions: Optional[PresetAssumptions] = None,
    ) -> dict[str, Any]:
        preset = self._owned(user_id, ticker, preset_id)
        if name is not None:
            cleaned = name.strip()
            if cleaned and cleaned != preset.name:
                if self.repo.get_by_name(user_id, preset.ticker, cleaned) is not None:
                    raise AppError(ErrorCode.CONFLICT, f"预设「{cleaned}」已存在", 409)
                preset.name = cleaned
        if assumptions is not None:
            preset.assumptions_json = assumptions.model_dump_json()
        self.db.commit()
        self.db.refresh(preset)
        return self._serialize(preset)

    def delete(self, user_id: int, ticker: str, preset_id: int) -> dict[str, Any]:
        preset = self._owned(user_id, ticker, preset_id)
        self.repo.delete(preset)
        self.db.commit()
        return {"id": preset_id, "deleted": True}

    # ------------------------------------------------------------------
    def _owned(self, user_id: int, ticker: str, preset_id: int) -> ValuationPreset:
        preset = self.repo.get(user_id, preset_id)
        if preset is None or preset.ticker != normalize_ticker(ticker):
            raise AppError(ErrorCode.NOT_FOUND, "预设不存在", 404)
        return preset

    @staticmethod
    def _serialize(preset: ValuationPreset) -> dict[str, Any]:
        try:
            raw = json.loads(preset.assumptions_json or "{}")
        except ValueError:
            raw = {}
        assumptions = PresetAssumptions.model_validate(raw) if isinstance(raw, dict) else PresetAssumptions()
        return {
            "id": preset.id,
            "ticker": preset.ticker,
            "name": preset.name,
            "assumptions": assumptions.model_dump(),
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        }
