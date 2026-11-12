"""估值接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.core.errors import AppError, ErrorCode
from app.schemas.common import ApiResponse, Meta
from app.schemas.valuation import (
    ReverseOut,
    ReverseRequest,
    ScenarioRequest,
    ScenariosOut,
    ValuationOut,
    WaccOut,
)
from app.services.market_service import MarketService
from app.services.valuation_service import ValuationService

router = APIRouter(prefix="/stocks", tags=["valuation"])


def _service(ticker: str) -> tuple[ValuationService, dict]:
    market = MarketService()
    quote, meta = market.get_quote(ticker)
    try:
        financials, _ = market.get_financials(ticker)
    except AppError:
        financials = None
    return ValuationService(quote, financials), meta


@router.get("/{ticker}/valuation")
def get_valuation(
    ticker: str,
    user: CurrentUser,
    growth: float | None = Query(default=None, ge=-100, le=200),
    terminal: float | None = Query(default=None, ge=-50, le=50),
    discount: float | None = Query(default=None, ge=0.1, le=100),
    ddm_growth: float | None = Query(default=None, ge=-50, le=50),
    years1: int | None = Query(default=None, ge=1, le=20),
) -> ApiResponse[ValuationOut]:
    service, meta = _service(ticker)
    result = service.build(
        growth=growth, terminal=terminal, discount=discount,
        ddm_growth=ddm_growth, years1=years1,
    )
    return ApiResponse(data=ValuationOut.model_validate(result), meta=Meta(**meta))


@router.post("/{ticker}/valuation/scenarios")
def post_scenarios(
    ticker: str, payload: ScenarioRequest, user: CurrentUser
) -> ApiResponse[ScenariosOut]:
    service, meta = _service(ticker)
    result = service.scenarios(payload.scenarios)
    if result.get("error"):
        raise AppError(ErrorCode.UNPROCESSABLE, result["error"], 422)
    return ApiResponse(data=ScenariosOut.model_validate(result), meta=Meta(**meta))


@router.post("/{ticker}/valuation/reverse")
def post_reverse(
    ticker: str, payload: ReverseRequest, user: CurrentUser
) -> ApiResponse[ReverseOut]:
    service, meta = _service(ticker)
    result = service.reverse(
        price=payload.price, terminal=payload.terminal,
        discount=payload.discount, years1=payload.years1,
    )
    return ApiResponse(data=ReverseOut.model_validate(result), meta=Meta(**meta))


@router.get("/{ticker}/valuation/wacc")
def get_wacc(
    ticker: str,
    user: CurrentUser,
    risk_free: float | None = Query(default=None, ge=0, le=50),
    beta: float | None = Query(default=None, ge=0, le=10),
    erp: float = Query(default=5.0, ge=0, le=30),
    cost_of_debt: float = Query(default=4.0, ge=0, le=50),
    tax_rate: float = Query(default=21.0, ge=0, le=100),
) -> ApiResponse[WaccOut]:
    service, meta = _service(ticker)
    result = service.wacc_params(
        risk_free=risk_free, beta=beta, erp=erp,
        cost_of_debt=cost_of_debt, tax_rate=tax_rate,
    )
    return ApiResponse(data=WaccOut.model_validate(result), meta=Meta(**meta))
