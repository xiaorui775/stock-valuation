"""估值预设接口（FR-VAL-07）。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, Meta
from app.schemas.preset import (
    DeletedOut,
    PresetComparisonOut,
    PresetCreate,
    PresetListOut,
    PresetOut,
    PresetUpdate,
)
from app.services.preset_compare_service import PresetCompareService
from app.services.preset_service import PresetService

router = APIRouter(prefix="/stocks", tags=["valuation"])


@router.get("/{ticker}/valuation/presets")
def list_presets(
    ticker: str, user: CurrentUser, db: DbSession
) -> ApiResponse[PresetListOut]:
    items = PresetService(db).list(user.id, ticker)
    return ApiResponse(
        data=PresetListOut(items=[PresetOut.model_validate(item) for item in items]),
        meta=Meta(source="local"),
    )


@router.get("/{ticker}/valuation/presets/compare")
def compare_presets(
    ticker: str,
    user: CurrentUser,
    db: DbSession,
    ids: Annotated[list[int] | None, Query(description="要对比的预设 ID，可重复")] = None,
) -> ApiResponse[PresetComparisonOut]:
    """按同一份行情/财报计算多个预设，便于比较假设差异（FR-RESEARCH-02）。"""
    data, meta = PresetCompareService(db).compare(user.id, ticker, ids)
    return ApiResponse(
        data=PresetComparisonOut.model_validate(data),
        meta=Meta(**meta),
    )


@router.post("/{ticker}/valuation/presets", status_code=status.HTTP_201_CREATED)
def create_preset(
    ticker: str, payload: PresetCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[PresetOut]:
    preset = PresetService(db).create(user.id, ticker, payload.name, payload.assumptions)
    return ApiResponse(data=PresetOut.model_validate(preset), meta=Meta(source="local"))


@router.patch("/{ticker}/valuation/presets/{preset_id}")
def update_preset(
    ticker: str,
    preset_id: int,
    payload: PresetUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[PresetOut]:
    preset = PresetService(db).update(
        user.id, ticker, preset_id, name=payload.name, assumptions=payload.assumptions
    )
    return ApiResponse(data=PresetOut.model_validate(preset), meta=Meta(source="local"))


@router.delete("/{ticker}/valuation/presets/{preset_id}")
def delete_preset(
    ticker: str, preset_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = PresetService(db).delete(user.id, ticker, preset_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))
