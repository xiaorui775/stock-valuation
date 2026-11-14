"""常用对比组合服务（FR-RESEARCH-06）。

保存 2–6 只标的的命名组合，代码统一规范化去重；按用户隔离，重名返回 409。
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.models.compare_preset import ComparePreset
from app.repositories.compare_preset_repo import ComparePresetRepository
from app.schemas.compare_preset import ComparePresetCreate, ComparePresetUpdate

MIN_TICKERS = 2
MAX_TICKERS = 6


class ComparePresetService:
    def __init__(self, db: OrmSession) -> None:
        self.db = db
        self.repo = ComparePresetRepository(db)

    def list(self, user_id: int) -> list[dict[str, Any]]:
        return [self._serialize(item) for item in self.repo.list_for(user_id)]

    def create(self, user_id: int, payload: ComparePresetCreate) -> dict[str, Any]:
        name = payload.name
        if self.repo.get_by_name(user_id, name) is not None:
            raise AppError(ErrorCode.CONFLICT, f"对比组合「{name}」已存在", 409)
        tickers = self._clean_tickers(payload.tickers)
        preset = self.repo.add(
            ComparePreset(
                user_id=user_id,
                name=name,
                tickers_json=json.dumps(tickers),
            )
        )
        self.db.commit()
        self.db.refresh(preset)
        return self._serialize(preset)

    def update(
        self, user_id: int, preset_id: int, payload: ComparePresetUpdate
    ) -> dict[str, Any]:
        preset = self._owned(user_id, preset_id)
        if payload.name is not None and payload.name != preset.name:
            if self.repo.get_by_name(user_id, payload.name) is not None:
                raise AppError(
                    ErrorCode.CONFLICT, f"对比组合「{payload.name}」已存在", 409
                )
            preset.name = payload.name
        if payload.tickers is not None:
            preset.tickers_json = json.dumps(self._clean_tickers(payload.tickers))
        self.db.commit()
        self.db.refresh(preset)
        return self._serialize(preset)

    def delete(self, user_id: int, preset_id: int) -> dict[str, Any]:
        preset = self._owned(user_id, preset_id)
        self.repo.delete(preset)
        self.db.commit()
        return {"id": preset_id, "deleted": True}

    # ------------------------------------------------------------------
    def _owned(self, user_id: int, preset_id: int) -> ComparePreset:
        preset = self.repo.get(user_id, preset_id)
        if preset is None:
            raise AppError(ErrorCode.NOT_FOUND, "对比组合不存在", 404)
        return preset

    @staticmethod
    def _clean_tickers(tickers: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in tickers:
            symbol = normalize_ticker(raw)
            if symbol and symbol not in cleaned:
                cleaned.append(symbol)
        if len(cleaned) < MIN_TICKERS:
            raise AppError(
                ErrorCode.UNPROCESSABLE,
                f"请至少保留 {MIN_TICKERS} 只不同的标的",
                422,
            )
        if len(cleaned) > MAX_TICKERS:
            raise AppError(
                ErrorCode.UNPROCESSABLE, f"最多保存 {MAX_TICKERS} 只标的", 422
            )
        return cleaned

    @staticmethod
    def _serialize(preset: ComparePreset) -> dict[str, Any]:
        try:
            tickers = json.loads(preset.tickers_json or "[]")
        except ValueError:
            tickers = []
        return {
            "id": preset.id,
            "name": preset.name,
            "tickers": tickers if isinstance(tickers, list) else [],
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        }
