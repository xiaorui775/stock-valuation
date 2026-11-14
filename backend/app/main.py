"""FastAPI 应用入口。"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    auth,
    compare,
    notes,
    portfolios,
    presets,
    screener,
    search,
    stocks,
    valuation,
    watchlists,
)
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIdMiddleware
from app.schemas.common import ApiResponse, Meta

settings = get_settings()
configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.run_migrations:
        _run_migrations()
    logger.info("startup", env=settings.env, demo=settings.demo, scheduler=settings.enable_scheduler)
    yield
    logger.info("shutdown")


def _run_migrations() -> None:
    """启动时自动升级数据库到最新版本。"""
    import subprocess
    import sys
    from pathlib import Path

    backend_root = Path(__file__).resolve().parent.parent
    alembic_ini = backend_root / "alembic.ini"
    if not alembic_ini.exists():
        logger.warning("migrations_skipped", reason="alembic.ini not found")
        return
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        env={**os.environ, "STOCKVAL_DATABASE_URL": settings.database_url},
    )
    if result.returncode != 0:
        logger.error("migrations_failed", stderr=result.stderr[-500:])
    else:
        logger.info("migrations_applied")


app = FastAPI(
    title="StockVal API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(stocks.router, prefix="/api/v1")
app.include_router(valuation.router, prefix="/api/v1")
app.include_router(presets.router, prefix="/api/v1")
app.include_router(watchlists.router, prefix="/api/v1")
app.include_router(portfolios.router, prefix="/api/v1")
app.include_router(compare.router, prefix="/api/v1")
app.include_router(screener.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readyz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/ping", tags=["health"])
async def ping() -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"pong": "ok"}, meta=Meta(source="api"))


def create_app() -> FastAPI:
    return app