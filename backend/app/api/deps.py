"""API 依赖：数据库会话、当前用户。"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as OrmSession

from app.core.db import get_db
from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.services.auth_service import SESSION_COOKIE, AuthService

DbSession = Annotated[OrmSession, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AppError(ErrorCode.UNAUTHORIZED, "请先登录", 401)
    user = AuthService(db).authenticate_token(token)
    if user is None:
        raise AppError(ErrorCode.UNAUTHORIZED, "会话已过期，请重新登录", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
