"""认证接口。"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode
from app.schemas.auth import (
    BootstrapRequest,
    LoginRequest,
    UpdateProfileRequest,
    UserOut,
)
from app.schemas.common import ApiResponse, Meta
from app.services.auth_service import SESSION_COOKIE, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def auth_status(db: DbSession) -> ApiResponse[dict]:
    service = AuthService(db)
    return ApiResponse(
        data={"initialized": service.is_initialized()},
        meta=Meta(source="local"),
    )


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap(payload: BootstrapRequest, request: Request, response: Response, db: DbSession) -> ApiResponse[UserOut]:
    service = AuthService(db)
    if service.is_initialized():
        raise AppError(ErrorCode.CONFLICT, "系统已完成初始化，无法重复创建账号", 409)
    user = service.bootstrap(payload)
    _user, token, expires = service.login(
        LoginRequest(email=user.email, password=payload.password), request.headers.get("user-agent"), request.client.host if request.client else None
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        expires=expires,
    )
    return ApiResponse(data=UserOut.model_validate(user), meta=Meta(source="local"))


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession) -> ApiResponse[UserOut]:
    service = AuthService(db)
    user, token, expires = service.login(
        payload, request.headers.get("user-agent"), request.client.host if request.client else None
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        expires=expires,
    )
    return ApiResponse(data=UserOut.model_validate(user), meta=Meta(source="local"))


@router.post("/logout")
def logout(request: Request, response: Response, db: DbSession) -> ApiResponse[dict]:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        AuthService(db).logout(token)
    response.delete_cookie(SESSION_COOKIE)
    return ApiResponse(data={"ok": True}, meta=Meta(source="local"))


@router.get("/me")
def me(user: CurrentUser) -> ApiResponse[UserOut]:
    return ApiResponse(data=UserOut.model_validate(user), meta=Meta(source="local"))


@router.patch("/me")
def update_me(payload: UpdateProfileRequest, user: CurrentUser, db: DbSession) -> ApiResponse[UserOut]:
    updated = AuthService(db).update_profile(user, payload)
    return ApiResponse(data=UserOut.model_validate(updated), meta=Meta(source="local"))
