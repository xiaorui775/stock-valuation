"""筛选预设的增删改查（§5.11 FR-SCR-04）。

预设保存的是完整请求体（股票池 + 条件 + 排序 + 分页大小），加载后可直接重跑，
因此存储的是 JSON 原文，不做字段裁剪，避免「保存时少一项、加载时行为不同」。
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.models.screener import ScreenerPreset
from app.repositories.screener_repo import ScreenerPresetRepository


class ScreenerPresetService:
    def __init__(self, db: OrmSession) -> None:
        self.db = db
        self.repo = ScreenerPresetRepository(db)

    def list(self, user_id: int) -> list[dict[str, Any]]:
        return [self._serialize(preset) for preset in self.repo.list(user_id)]

    def create(self, user_id: int, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._clean_name(name)
        if self.repo.get_by_name(user_id, cleaned) is not None:
            raise AppError(ErrorCode.CONFLICT, f"筛选预设「{cleaned}」已存在", 409)
        preset = self.repo.add(
            ScreenerPreset(
                user_id=user_id,
                name=cleaned,
                payload=json.dumps(payload, ensure_ascii=False),
            )
        )
        self.db.commit()
        self.db.refresh(preset)
        return self._serialize(preset)

    def update(
        self, user_id: int, preset_id: int, name: str | None, payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        preset = self._owned(user_id, preset_id)
        if name is not None:
            cleaned = self._clean_name(name)
            if cleaned != preset.name:
                if self.repo.get_by_name(user_id, cleaned) is not None:
                    raise AppError(ErrorCode.CONFLICT, f"筛选预设「{cleaned}」已存在", 409)
                preset.name = cleaned
        if payload is not None:
            preset.payload = json.dumps(payload, ensure_ascii=False)
        self.db.commit()
        self.db.refresh(preset)
        return self._serialize(preset)

    def delete(self, user_id: int, preset_id: int) -> dict[str, Any]:
        preset = self._owned(user_id, preset_id)
        self.repo.delete(preset)
        self.db.commit()
        return {"id": preset_id, "deleted": True}

    # ------------------------------------------------------------------
    def _owned(self, user_id: int, preset_id: int) -> ScreenerPreset:
        preset = self.repo.get(user_id, preset_id)
        if preset is None:
            raise AppError(ErrorCode.NOT_FOUND, "筛选预设不存在", 404)
        return preset

    @staticmethod
    def _serialize(preset: ScreenerPreset) -> dict[str, Any]:
        return {
            "id": preset.id,
            "name": preset.name,
            "payload": json.loads(preset.payload),
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        }

    @staticmethod
    def _clean_name(name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise AppError(ErrorCode.UNPROCESSABLE, "预设名称不能为空", 422)
        return cleaned
