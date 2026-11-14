"""研究笔记接口测试（FR-RESEARCH-03）。"""
from __future__ import annotations

import pytest

BASE = "/api/v1/notes"
PRESETS = "/api/v1/stocks"


def _create(client, **overrides):
    payload = {
        "ticker": "AAPL",
        "kind": "conclusion",
        "title": "估值偏低",
        "content": "DCF 上行约 20%，需要复核折现率假设。",
        "is_resolved": False,
    }
    payload.update(overrides)
    return client.post(BASE, json=payload)


def _create_preset(client, ticker: str = "AAPL", name: str = "保守假设"):
    return client.post(
        f"{PRESETS}/{ticker}/valuation/presets",
        json={
            "name": name,
            "assumptions": {"growth": 5, "terminal": 2, "discount": 11},
        },
    )


def _list(client, **params):
    return client.get(BASE, params=params)


def test_notes_require_auth(client):
    assert _list(client).status_code == 401
    assert _create(client).status_code == 401


def test_create_and_filter_by_ticker(initialized_client):
    apple = _create(initialized_client).json()["data"]
    assert apple["ticker"] == "AAPL"
    assert apple["kind"] == "conclusion"
    assert apple["preset_id"] is None
    assert apple["preset_name"] is None

    _create(initialized_client, ticker="MSFT", title="微软笔记")

    # ticker 归一化：小写也能查到
    aapl = _list(initialized_client, ticker="aapl").json()["data"]
    assert aapl["total"] == 1
    assert aapl["items"][0]["id"] == apple["id"]

    everything = _list(initialized_client).json()["data"]
    assert everything["total"] == 2


def test_filter_by_kind_and_keyword(initialized_client):
    _create(
        initialized_client,
        kind="conclusion",
        title="毛利率改善",
        content="服务收入占比提升。",
    )
    _create(
        initialized_client,
        kind="question",
        title="财报日期确认",
        content="需要核对下一次财报日。",
    )

    questions = _list(initialized_client, ticker="AAPL", kind="question").json()["data"]
    assert questions["total"] == 1
    assert questions["items"][0]["kind"] == "question"

    by_title = _list(initialized_client, ticker="AAPL", q="毛利率").json()["data"]
    assert by_title["total"] == 1

    # 关键词也匹配正文
    by_content = _list(initialized_client, ticker="AAPL", q="服务收入").json()["data"]
    assert by_content["total"] == 1

    empty = _list(initialized_client, ticker="AAPL", q="不存在的关键词").json()["data"]
    assert empty["total"] == 0


def test_update_note_fields_and_resolved_state(initialized_client):
    note = _create(
        initialized_client, kind="question", title="待验证问题", content="先占位"
    ).json()["data"]

    resp = initialized_client.patch(
        f"{BASE}/{note['id']}",
        json={
            "kind": "question",
            "title": "待验证：毛利率能否维持",
            "content": "观察下两个季度。",
            "is_resolved": True,
        },
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["title"] == "待验证：毛利率能否维持"
    assert updated["is_resolved"] is True

    # 改成普通笔记后不再保留「已解决」
    resp = initialized_client.patch(f"{BASE}/{note['id']}", json={"kind": "note"})
    assert resp.status_code == 200
    assert resp.json()["data"]["is_resolved"] is False


def test_note_links_to_same_ticker_preset(initialized_client):
    preset = _create_preset(initialized_client).json()["data"]
    note = _create(initialized_client, preset_id=preset["id"]).json()["data"]
    assert note["preset_id"] == preset["id"]
    assert note["preset_name"] == "保守假设"

    # 显式传 null 解除关联
    resp = initialized_client.patch(f"{BASE}/{note['id']}", json={"preset_id": None})
    assert resp.status_code == 200
    assert resp.json()["data"]["preset_id"] is None
    assert resp.json()["data"]["preset_name"] is None


def test_note_rejects_preset_from_other_ticker(initialized_client):
    msft_preset = _create_preset(
        initialized_client, ticker="MSFT", name="微软预设"
    ).json()["data"]

    resp = _create(initialized_client, ticker="AAPL", preset_id=msft_preset["id"])
    assert resp.status_code == 404
    assert "不属于该标的" in resp.json()["error"]["message"]


def test_note_rejects_unknown_preset(initialized_client):
    resp = _create(initialized_client, preset_id=99999)
    assert resp.status_code == 404


def test_delete_note(initialized_client):
    note = _create(initialized_client).json()["data"]
    resp = initialized_client.delete(f"{BASE}/{note['id']}")
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] is True

    assert _list(initialized_client, ticker="AAPL").json()["data"]["total"] == 0
    again = initialized_client.delete(f"{BASE}/{note['id']}")
    assert again.status_code == 404


def test_notes_validation(initialized_client):
    assert _create(initialized_client, title="   ").status_code == 422
    assert _create(initialized_client, kind="unknown").status_code == 422
    assert _create(initialized_client, title="x" * 201).status_code == 422
    assert _list(initialized_client, kind="unknown").status_code == 422


def test_notes_are_scoped_to_user(initialized_client):
    """另一个用户看不到、也改不了当前用户的笔记。"""
    from app.core.db import SessionLocal
    from app.core.errors import AppError
    from app.models.user import User
    from app.schemas.note import NoteUpdate
    from app.services.note_service import ResearchNoteService

    note = _create(initialized_client).json()["data"]

    db = SessionLocal()
    try:
        other = User(email="other@example.com", display_name="other", password_hash="x")
        db.add(other)
        db.commit()
        db.refresh(other)

        service = ResearchNoteService(db)
        assert service.list(other.id)["total"] == 0
        with pytest.raises(AppError) as excinfo:
            service.update(other.id, note["id"], NoteUpdate(title="越权修改"))
        assert excinfo.value.status_code == 404
    finally:
        db.close()
