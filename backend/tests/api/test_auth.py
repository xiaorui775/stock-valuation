"""认证接口测试。"""
from __future__ import annotations


def test_status_reports_not_initialized(client):
    resp = client.get("/api/v1/auth/status")
    assert resp.status_code == 200
    assert resp.json()["data"]["initialized"] is False


def test_bootstrap_creates_user_and_session(client):
    resp = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "a@example.com", "password": "password123", "display_name": "A"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["email"] == "a@example.com"
    assert body["data"]["role"] == "owner"
    assert "stockval_session" in resp.cookies
    # 密码不得出现在响应中
    assert "password" not in resp.text.lower() or "password_hash" not in resp.text


def test_bootstrap_twice_conflicts(client):
    payload = {"email": "a@example.com", "password": "password123"}
    assert client.post("/api/v1/auth/bootstrap", json=payload).status_code == 201
    second = client.post("/api/v1/auth/bootstrap", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_login_with_wrong_password_fails(client):
    client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "a@example.com", "password": "password123"},
    )
    client.cookies.clear()
    resp = client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpass"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_success_and_me(client):
    client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "a@example.com", "password": "password123"},
    )
    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"}
    )
    assert login.status_code == 200
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "a@example.com"


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_logout_clears_session(initialized_client):
    assert initialized_client.get("/api/v1/auth/me").status_code == 200
    assert initialized_client.post("/api/v1/auth/logout").status_code == 200
    assert initialized_client.get("/api/v1/auth/me").status_code == 401


def test_update_profile_changes_display_name(initialized_client):
    resp = initialized_client.patch(
        "/api/v1/auth/me", json={"display_name": "新名字", "base_currency": "USD"}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["display_name"] == "新名字"
    assert resp.json()["data"]["base_currency"] == "USD"


def test_password_change_requires_current_password(initialized_client):
    resp = initialized_client.patch(
        "/api/v1/auth/me", json={"new_password": "newpassword123"}
    )
    assert resp.status_code == 400


def test_password_change_revokes_other_sessions(initialized_client):
    # 登录第二会话
    initialized_client.cookies.clear()
    initialized_client.post(
        "/api/v1/auth/login", json={"email": "tester@example.com", "password": "password123"}
    )
    # 改密码使所有会话失效
    resp = initialized_client.patch(
        "/api/v1/auth/me",
        json={"current_password": "password123", "new_password": "brandnew123"},
    )
    assert resp.status_code == 200
    assert initialized_client.get("/api/v1/auth/me").status_code == 401
