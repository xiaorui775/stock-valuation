"""应用配置：从 .env 与环境变量读取。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STOCKVAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    secret_key: str = "dev-insecure-change-me"
    database_url: str = "sqlite:///./data/stockval.db"
    data_dir: Path = Path("./data")
    run_migrations: bool = True
    enable_scheduler: bool = True
    demo: bool = False
    # NoDecode：环境变量写 `a,b` 而不是 JSON 数组（docker-compose / .env 里这样更自然）。
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    log_level: str = "INFO"
    report_retention_days: int = 30
    cache_ttl_quote_seconds: int = 45
    cache_ttl_history_seconds: int = 600
    cache_ttl_financials_hours: int = 12
    cache_ttl_news_minutes: int = 15
    cache_ttl_announcements_minutes: int = 60
    cache_ttl_metadata_hours: int = 24
    cache_ttl_fx_minutes: int = 60

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """支持 `a,b` 与 JSON 数组两种写法；空串表示不限制来源（用 `*`）。"""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
