"""多股对比接口（§5.10 FR-CMP-01 ~ 04）。"""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, Meta
from app.schemas.compare import CompareOut
from app.schemas.compare_preset import (
    ComparePresetCreate,
    ComparePresetListOut,
    ComparePresetOut,
    ComparePresetUpdate,
)
from app.schemas.preset import DeletedOut
from app.services.compare_preset_service import ComparePresetService
from app.services.compare_service import CompareService

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/presets")
def list_compare_presets(
    user: CurrentUser, db: DbSession
) -> ApiResponse[ComparePresetListOut]:
    items = ComparePresetService(db).list(user.id)
    return ApiResponse(
        data=ComparePresetListOut(
            items=[ComparePresetOut.model_validate(item) for item in items]
        ),
        meta=Meta(source="local"),
    )


@router.post("/presets", status_code=status.HTTP_201_CREATED)
def create_compare_preset(
    payload: ComparePresetCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[ComparePresetOut]:
    item = ComparePresetService(db).create(user.id, payload)
    return ApiResponse(data=ComparePresetOut.model_validate(item), meta=Meta(source="local"))


@router.patch("/presets/{preset_id}")
def update_compare_preset(
    preset_id: int,
    payload: ComparePresetUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[ComparePresetOut]:
    item = ComparePresetService(db).update(user.id, preset_id, payload)
    return ApiResponse(data=ComparePresetOut.model_validate(item), meta=Meta(source="local"))


@router.delete("/presets/{preset_id}")
def delete_compare_preset(
    preset_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = ComparePresetService(db).delete(user.id, preset_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))


@router.get("")
def compare(
    user: CurrentUser,
    tickers: str = Query(..., description="逗号分隔的代码，2–6 只，例如 AAPL,MSFT"),
    period: str = Query("1y", description="归一化走势区间，例如 1y / 6mo / 3mo"),
) -> ApiResponse[CompareOut]:
    data = CompareService().compare(tickers.split(","), period)
    return ApiResponse(
        data=CompareOut.model_validate(data),
        meta=Meta(source="mixed", as_of=data.get("as_of")),
    )
