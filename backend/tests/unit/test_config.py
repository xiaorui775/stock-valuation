"""配置解析测试：环境变量里列表字段的写法。"""
from __future__ import annotations

from app.core.config import Settings


def test_allowed_origins_from_comma_separated_env(monkeypatch):
    """docker-compose / .env 里写 `a,b` 不应触发 SettingsError。"""
    monkeypatch.setenv(
        "STOCKVAL_ALLOWED_ORIGINS", "http://localhost:8080, https://a.example"
    )
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == ["http://localhost:8080", "https://a.example"]


def test_allowed_origins_from_json_env(monkeypatch):
    monkeypatch.setenv("STOCKVAL_ALLOWED_ORIGINS", '["http://x", "http://y"]')
    assert Settings(_env_file=None).allowed_origins == ["http://x", "http://y"]


def test_allowed_origins_single_value(monkeypatch):
    monkeypatch.setenv("STOCKVAL_ALLOWED_ORIGINS", "http://localhost:8080")
    assert Settings(_env_file=None).allowed_origins == ["http://localhost:8080"]


def test_allowed_origins_default(monkeypatch):
    monkeypatch.delenv("STOCKVAL_ALLOWED_ORIGINS", raising=False)
    settings = Settings(_env_file=None)
    assert "http://localhost:5173" in settings.allowed_origins


def test_run_migrations_default_and_override(monkeypatch):
    """测试环境关掉启动迁移：每个 TestClient 启动都会开一个 alembic 子进程。"""
    monkeypatch.delenv("STOCKVAL_RUN_MIGRATIONS", raising=False)
    assert Settings(_env_file=None).run_migrations is True
    monkeypatch.setenv("STOCKVAL_RUN_MIGRATIONS", "0")
    assert Settings(_env_file=None).run_migrations is False
