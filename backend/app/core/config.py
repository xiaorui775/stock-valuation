"""应用配置：从 .env 与环境变量读取。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    enable_scheduler: bool = True
    demo: bool = False
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    log_level: str = "INFO"
    report_retention_days: int = 30
    cache_ttl_quote_seconds: int = 45
    cache_ttl_history_seconds: int = 600
    cache_ttl_financials_hours: int = 12
    cache_ttl_news_minutes: int = 15
    cache_ttl_announcements_minutes: int = 60
    cache_ttl_metadata_hours: int = 24
    cache_ttl_fx_minutes: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
