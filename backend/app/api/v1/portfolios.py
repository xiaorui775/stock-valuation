"""投资组合接口（FR-PORT-01 / 02）。"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, Meta
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingOut,
    HoldingUpdate,
    PortfolioCreate,
    PortfolioListOut,
    PortfolioOut,
    PortfolioSummaryOut,
    PortfolioUpdate,
)
from app.schemas.preset import DeletedOut
from app.services.portfolio_service import PortfolioService
from app.services.portfolio_summary_service import PortfolioSummaryService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("")
def list_portfolios(user: CurrentUser, db: DbSession) -> ApiResponse[PortfolioListOut]:
    items = PortfolioService(db).list(user.id)
    return ApiResponse(
        data=PortfolioListOut(
            items=[PortfolioOut.model_validate(item) for item in items]
        ),
        meta=Meta(source="local"),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[PortfolioOut]:
    portfolio = PortfolioService(db).create(
        user.id, payload.name, payload.base_currency, payload.note
    )
    return ApiResponse(
        data=PortfolioOut.model_validate(portfolio), meta=Meta(source="local")
    )


@router.get("/{portfolio_id}")
def get_portfolio(
    portfolio_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[PortfolioOut]:
    portfolio = PortfolioService(db).get(user.id, portfolio_id)
    return ApiResponse(
        data=PortfolioOut.model_validate(portfolio), meta=Meta(source="local")
    )


@router.patch("/{portfolio_id}")
def update_portfolio(
    portfolio_id: int, payload: PortfolioUpdate, user: CurrentUser, db: DbSession
) -> ApiResponse[PortfolioOut]:
    portfolio = PortfolioService(db).update(
        user.id,
        portfolio_id,
        name=payload.name,
        base_currency=payload.base_currency,
        note=payload.note,
    )
    return ApiResponse(
        data=PortfolioOut.model_validate(portfolio), meta=Meta(source="local")
    )


@router.delete("/{portfolio_id}")
def delete_portfolio(
    portfolio_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = PortfolioService(db).delete(user.id, portfolio_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))


@router.get("/{portfolio_id}/summary")
def portfolio_summary(
    portfolio_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[PortfolioSummaryOut]:
    """组合汇总：市值、盈亏、权重、汇率与分布（FR-PORT-03 / 04 / 07）。"""
    data = PortfolioSummaryService(db).summary(user.id, portfolio_id)
    return ApiResponse(
        data=PortfolioSummaryOut.model_validate(data),
        meta=Meta(source="mixed", as_of=data.get("as_of")),
    )


@router.get("/{portfolio_id}/holdings")
def list_holdings(
    portfolio_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[list[HoldingOut]]:
    items = PortfolioService(db).list_holdings(user.id, portfolio_id)
    return ApiResponse(
        data=[HoldingOut.model_validate(item) for item in items],
        meta=Meta(source="local"),
    )


@router.post("/{portfolio_id}/holdings", status_code=status.HTTP_201_CREATED)
def add_holding(
    portfolio_id: int, payload: HoldingCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[HoldingOut]:
    holding = PortfolioService(db).add_holding(
        user.id,
        portfolio_id,
        ticker=payload.ticker,
        quantity=payload.quantity,
        avg_cost=payload.avg_cost,
        currency=payload.currency,
        opened_on=payload.opened_on,
        note=payload.note,
    )
    return ApiResponse(data=HoldingOut.model_validate(holding), meta=Meta(source="local"))


@router.patch("/{portfolio_id}/holdings/{holding_id}")
def update_holding(
    portfolio_id: int,
    holding_id: int,
    payload: HoldingUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ApiResponse[HoldingOut]:
    holding = PortfolioService(db).update_holding(
        user.id,
        portfolio_id,
        holding_id,
        quantity=payload.quantity,
        avg_cost=payload.avg_cost,
        currency=payload.currency,
        opened_on=payload.opened_on,
        note=payload.note,
    )
    return ApiResponse(data=HoldingOut.model_validate(holding), meta=Meta(source="local"))


@router.delete("/{portfolio_id}/holdings/{holding_id}")
def delete_holding(
    portfolio_id: int, holding_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = PortfolioService(db).delete_holding(user.id, portfolio_id, holding_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))
