"""标的搜索接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.common import ApiResponse, Meta
from app.schemas.stocks import InstrumentOut
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    user: CurrentUser,
    q: str = Query(min_length=1, max_length=64),
    market: str | None = Query(default=None, pattern="^(US|HK|CN)$"),
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[InstrumentOut]]:
    """按代码或公司名称搜索标的。

    结果为空不是错误，返回空列表由前端展示空状态。
    """
    items, meta = SearchService().search(q, market, limit)
    return ApiResponse(
        data=[InstrumentOut.model_validate(i) for i in items],
        meta=Meta(**meta),
    )
