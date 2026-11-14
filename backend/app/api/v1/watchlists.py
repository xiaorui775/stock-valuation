"""自选股接口（FR-WATCH-01 / 02）。"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, Meta
from app.schemas.preset import DeletedOut
from app.schemas.watchlist import (
    BatchItemCreate,
    BatchResultOut,
    GroupCreate,
    GroupOrderUpdate,
    GroupUpdate,
    ItemCreate,
    ItemOrderUpdate,
    WatchlistGroupOut,
    WatchlistItemOut,
    WatchlistListOut,
    WatchlistQuotesOut,
)
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


def _groups(items: list[dict]) -> WatchlistListOut:
    return WatchlistListOut(
        groups=[WatchlistGroupOut.model_validate(item) for item in items]
    )


@router.get("")
def list_watchlists(user: CurrentUser, db: DbSession) -> ApiResponse[WatchlistListOut]:
    items = WatchlistService(db).list(user.id)
    return ApiResponse(data=_groups(items), meta=Meta(source="local"))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[WatchlistGroupOut]:
    group = WatchlistService(db).create_group(user.id, payload.name)
    return ApiResponse(
        data=WatchlistGroupOut.model_validate(group), meta=Meta(source="local")
    )


@router.patch("/order")
def reorder_groups(
    payload: GroupOrderUpdate, user: CurrentUser, db: DbSession
) -> ApiResponse[WatchlistListOut]:
    items = WatchlistService(db).reorder_groups(user.id, payload.group_ids)
    return ApiResponse(data=_groups(items), meta=Meta(source="local"))


@router.patch("/{group_id}")
def rename_group(
    group_id: int, payload: GroupUpdate, user: CurrentUser, db: DbSession
) -> ApiResponse[WatchlistGroupOut]:
    group = WatchlistService(db).rename_group(user.id, group_id, payload.name)
    return ApiResponse(
        data=WatchlistGroupOut.model_validate(group), meta=Meta(source="local")
    )


@router.delete("/{group_id}")
def delete_group(
    group_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = WatchlistService(db).delete_group(user.id, group_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))


@router.get("/{group_id}/quotes")
def group_quotes(
    group_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[WatchlistQuotesOut]:
    """分组的行情与估值列；单只失败只影响该行（FR-WATCH-05）。"""
    data = WatchlistService(db).quotes(user.id, group_id)
    return ApiResponse(
        data=WatchlistQuotesOut.model_validate(data), meta=Meta(source="mixed")
    )


@router.post("/{group_id}/items", status_code=status.HTTP_201_CREATED)
def add_item(
    group_id: int, payload: ItemCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[WatchlistItemOut]:
    item = WatchlistService(db).add_item(user.id, group_id, payload.ticker)
    return ApiResponse(
        data=WatchlistItemOut.model_validate(item), meta=Meta(source="local")
    )


@router.post("/{group_id}/items/batch")
def add_items(
    group_id: int, payload: BatchItemCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[BatchResultOut]:
    result = WatchlistService(db).add_items(user.id, group_id, payload.tickers)
    return ApiResponse(
        data=BatchResultOut.model_validate(result), meta=Meta(source="local")
    )


@router.patch("/{group_id}/items/order")
def reorder_items(
    group_id: int, payload: ItemOrderUpdate, user: CurrentUser, db: DbSession
) -> ApiResponse[list[WatchlistItemOut]]:
    items = WatchlistService(db).reorder_items(user.id, group_id, payload.item_ids)
    return ApiResponse(
        data=[WatchlistItemOut.model_validate(item) for item in items],
        meta=Meta(source="local"),
    )


@router.delete("/{group_id}/items/{item_id}")
def remove_item(
    group_id: int, item_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = WatchlistService(db).remove_item(user.id, group_id, item_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))
