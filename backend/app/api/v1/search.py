"""标的搜索接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.common import ApiResponse, Meta
from app.schemas.stocks import InstrumentOut
from app.services.market_service import MarketService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    user: CurrentUser,
    q: str = Query(min_length=1, max_length=64),
    market: str | None = Query(default=None, pattern="^(US|HK|CN)$"),
) -> ApiResponse[list[InstrumentOut]]:
    items, meta = MarketService().search(q, market)
    return ApiResponse(
        data=[InstrumentOut.model_validate(i) for i in items],
        meta=Meta(**meta),
    )
