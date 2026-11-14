"""筛选器接口：筛选、预设指数、筛选预设（§5.11 FR-SCR-01 ~ 06）。"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, Meta
from app.schemas.preset import DeletedOut
from app.schemas.screener import (
    IndexDetailOut,
    IndexRefreshOut,
    IndexSummaryOut,
    ScreenerOut,
    ScreenerPresetCreate,
    ScreenerPresetOut,
    ScreenerPresetUpdate,
    ScreenerRequest,
)
from app.services.index_service import IndexService
from app.services.screener_preset_service import ScreenerPresetService
from app.services.screener_service import ScreenerService

router = APIRouter(prefix="/screener", tags=["screener"])


@router.post("")
def screen(
    payload: ScreenerRequest, user: CurrentUser, db: DbSession
) -> ApiResponse[ScreenerOut]:
    """按条件筛选股票池；部分标的失败仍返回结果与失败原因。"""
    data = ScreenerService(db).run(
        user.id,
        pool_kind=payload.pool.kind,
        tickers=payload.pool.tickers,
        watchlist_id=payload.pool.watchlist_id,
        index_key=payload.pool.index_key,
        market_filter=payload.market,
        filters=[item.model_dump() for item in payload.filters],
        sort_key=payload.sort_key,
        sort_desc=payload.sort_desc,
        page=payload.page,
        page_size=payload.page_size,
    )
    return ApiResponse(
        data=ScreenerOut.model_validate(data),
        meta=Meta(source="mixed", as_of=data.get("as_of")),
    )


# ----------------------------------------------------------------------
# 预设指数成分（M2-13）
# ----------------------------------------------------------------------


@router.get("/indexes")
def list_indexes(user: CurrentUser, db: DbSession) -> ApiResponse[list[IndexSummaryOut]]:
    """三个预设指数的成分数量、来源与更新时间（不带完整名单）。"""
    data = IndexService(db).list()
    return ApiResponse(
        data=[IndexSummaryOut.model_validate(item) for item in data],
        meta=Meta(source="mixed"),
    )


@router.get("/indexes/{key}")
def get_index(key: str, user: CurrentUser, db: DbSession) -> ApiResponse[IndexDetailOut]:
    data = IndexService(db).get(key)
    return ApiResponse(
        data=IndexDetailOut.model_validate(data),
        meta=Meta(source=data.get("source")),
    )


@router.post("/indexes/{key}/refresh")
def refresh_index(
    key: str, user: CurrentUser, db: DbSession
) -> ApiResponse[IndexRefreshOut]:
    """从数据源刷新成分股；数据源不支持时保留现有名单并说明原因。"""
    data = IndexService(db).refresh(key)
    return ApiResponse(
        data=IndexRefreshOut.model_validate(data),
        meta=Meta(source=data.get("source")),
    )


# ----------------------------------------------------------------------
# 筛选预设（FR-SCR-04）
# ----------------------------------------------------------------------


@router.get("/presets")
def list_presets(
    user: CurrentUser, db: DbSession
) -> ApiResponse[list[ScreenerPresetOut]]:
    items = ScreenerPresetService(db).list(user.id)
    return ApiResponse(
        data=[ScreenerPresetOut.model_validate(item) for item in items],
        meta=Meta(source="local"),
    )


@router.post("/presets", status_code=status.HTTP_201_CREATED)
def create_preset(
    payload: ScreenerPresetCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[ScreenerPresetOut]:
    preset = ScreenerPresetService(db).create(
        user.id, payload.name, payload.payload.model_dump()
    )
    return ApiResponse(
        data=ScreenerPresetOut.model_validate(preset), meta=Meta(source="local")
    )


@router.patch("/presets/{preset_id}")
def update_preset(
    preset_id: int,
    payload: ScreenerPresetUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[ScreenerPresetOut]:
    preset = ScreenerPresetService(db).update(
        user.id,
        preset_id,
        payload.name,
        payload.payload.model_dump() if payload.payload else None,
    )
    return ApiResponse(
        data=ScreenerPresetOut.model_validate(preset), meta=Meta(source="local")
    )


@router.delete("/presets/{preset_id}")
def delete_preset(
    preset_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = ScreenerPresetService(db).delete(user.id, preset_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))
