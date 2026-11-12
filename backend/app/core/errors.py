"""统一错误模型与异常类型。"""
from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    TICKER_NOT_FOUND = "TICKER_NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNPROCESSABLE = "UNPROCESSABLE"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    INTERNAL = "INTERNAL"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ProviderUnavailable(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.UPSTREAM_ERROR, message, 502, details)


class TickerNotFound(AppError):
    def __init__(self, ticker: str) -> None:
        super().__init__(
            ErrorCode.TICKER_NOT_FOUND,
            f"找不到股票代码 {ticker}，或该代码暂无行情数据",
            404,
            {"ticker": ticker},
        )


class RateLimited(AppError):
    def __init__(self, message: str = "数据源限流，请稍后重试") -> None:
        super().__init__(ErrorCode.RATE_LIMITED, message, 429)


class DataUnavailable(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.DATA_UNAVAILABLE, message, 503, details)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code.value,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.VALIDATION_ERROR
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code.value,
                "message": str(exc.detail),
                "details": {},
                "request_id": request_id,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ErrorCode.INTERNAL.value,
                "message": "服务内部错误，请联系管理员",
                "details": {},
                "request_id": request_id,
            }
        },
    )
