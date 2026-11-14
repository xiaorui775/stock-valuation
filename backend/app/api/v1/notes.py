"""研究笔记接口（FR-RESEARCH-03）。"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, Meta
from app.schemas.note import NoteCreate, NoteKind, NoteListOut, NoteOut, NoteUpdate
from app.schemas.preset import DeletedOut
from app.services.note_service import ResearchNoteService

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("")
def list_notes(
    user: CurrentUser,
    db: DbSession,
    ticker: str | None = None,
    q: str | None = None,
    kind: NoteKind | None = None,
) -> ApiResponse[NoteListOut]:
    """按标的/关键词/类型筛选当前用户的研究笔记；不传 ticker 时跨标的返回。"""
    result = ResearchNoteService(db).list(user.id, ticker, q, kind)
    return ApiResponse(
        data=NoteListOut(
            items=[NoteOut.model_validate(item) for item in result["items"]],
            total=result["total"],
        ),
        meta=Meta(source="local"),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate, user: CurrentUser, db: DbSession
) -> ApiResponse[NoteOut]:
    note = ResearchNoteService(db).create(user.id, payload)
    return ApiResponse(data=NoteOut.model_validate(note), meta=Meta(source="local"))


@router.patch("/{note_id}")
def update_note(
    note_id: int, payload: NoteUpdate, user: CurrentUser, db: DbSession
) -> ApiResponse[NoteOut]:
    note = ResearchNoteService(db).update(user.id, note_id, payload)
    return ApiResponse(data=NoteOut.model_validate(note), meta=Meta(source="local"))


@router.delete("/{note_id}")
def delete_note(
    note_id: int, user: CurrentUser, db: DbSession
) -> ApiResponse[DeletedOut]:
    result = ResearchNoteService(db).delete(user.id, note_id)
    return ApiResponse(data=DeletedOut.model_validate(result), meta=Meta(source="local"))
