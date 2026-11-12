"""pytest 夹具：隔离的测试数据库与客户端。"""
from __future__ import annotations

import os
import tempfile

import pytest

# 必须在导入 app 之前设置环境变量
_tmpdir = tempfile.mkdtemp(prefix="stockval-test-")
os.environ["STOCKVAL_DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["STOCKVAL_SECRET_KEY"] = "test-secret-key"
os.environ["STOCKVAL_ENABLE_SCHEDULER"] = "0"
os.environ["STOCKVAL_DEMO"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from app.core.db import SessionLocal, engine
from app.main import app
from app.models import Base


@pytest.fixture(scope="function", autouse=True)
def fresh_db():
    """每个测试用独立库表，保证隔离。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> OrmSession:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def initialized_client(client: TestClient) -> TestClient:
    """已完成初始化并处于登录状态的客户端。"""
    resp = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "tester@example.com",
            "password": "password123",
            "display_name": "测试用户",
        },
    )
    assert resp.status_code == 201, resp.text
    return client
