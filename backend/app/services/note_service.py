"""研究笔记服务（FR-RESEARCH-03）。

按标的记录研究结论、关键假设与待验证问题，可关联同标的的估值预设。
所有读写按 user_id 隔离；关联预设必须属于当前用户且标的相同。
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.models.note import ResearchNote
from app.repositories.note_repo import ResearchNoteRepository
from app.repositories.preset_repo import PresetRepository
from app.schemas.note import NoteCreate, NoteUpdate


class ResearchNoteService:
    def __init__(self, db: OrmSession) -> None:
        self.db = db
        self.repo = ResearchNoteRepository(db)
        self.presets = PresetRepository(db)

    # ------------------------------------------------------------------
    def list(
        self,
        user_id: int,
        ticker: Optional[str] = None,
        query: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> dict[str, Any]:
        ticker_value = normalize_ticker(ticker) if ticker else None
        text = (query or "").strip() or None
        notes = self.repo.list_for(user_id, ticker_value, text, kind)
        names = self._preset_names(user_id, notes)
        items = [self._serialize(note, names) for note in notes]
        return {"items": items, "total": len(items)}

    def create(self, user_id: int, payload: NoteCreate) -> dict[str, Any]:
        ticker = normalize_ticker(payload.ticker)
        preset_id = self._validated_preset(user_id, ticker, payload.preset_id)
        note = self.repo.add(
            ResearchNote(
                user_id=user_id,
                ticker=ticker,
                kind=payload.kind,
                title=payload.title,
                content=self._clean_content(payload.content),
                preset_id=preset_id,
                is_resolved=payload.is_resolved if payload.kind == "question" else False,
            )
        )
        self.db.commit()
        self.db.refresh(note)
        return self._serialize(note, self._preset_names(user_id, [note]))

    def update(
        self, user_id: int, note_id: int, payload: NoteUpdate
    ) -> dict[str, Any]:
        note = self._owned(user_id, note_id)
        fields = payload.model_fields_set

        if payload.kind is not None:
            note.kind = payload.kind
        if payload.title is not None:
            note.title = payload.title
        if "content" in fields:
            note.content = self._clean_content(payload.content)
        if "preset_id" in fields:
            note.preset_id = self._validated_preset(user_id, note.ticker, payload.preset_id)
        if payload.is_resolved is not None:
            note.is_resolved = payload.is_resolved
        # 只有待验证问题才有「已解决」状态
        if note.kind != "question":
            note.is_resolved = False

        self.db.commit()
        self.db.refresh(note)
        return self._serialize(note, self._preset_names(user_id, [note]))

    def delete(self, user_id: int, note_id: int) -> dict[str, Any]:
        note = self._owned(user_id, note_id)
        self.repo.delete(note)
        self.db.commit()
        return {"id": note_id, "deleted": True}

    # ------------------------------------------------------------------
    def _owned(self, user_id: int, note_id: int) -> ResearchNote:
        note = self.repo.get(user_id, note_id)
        if note is None:
            raise AppError(ErrorCode.NOT_FOUND, "研究笔记不存在", 404)
        return note

    def _validated_preset(
        self, user_id: int, ticker: str, preset_id: Optional[int]
    ) -> Optional[int]:
        if preset_id is None:
            return None
        preset = self.presets.get(user_id, preset_id)
        if preset is None or preset.ticker != ticker:
            raise AppError(
                ErrorCode.NOT_FOUND, "估值预设不存在或不属于该标的", 404
            )
        return preset.id

    @staticmethod
    def _clean_content(content: Optional[str]) -> Optional[str]:
        if content is None:
            return None
        cleaned = content.strip()
        return cleaned or None

    def _preset_names(
        self, user_id: int, notes: list[ResearchNote]
    ) -> dict[int, str]:
        ids = [note.preset_id for note in notes if note.preset_id is not None]
        return {
            preset_id: preset.name
            for preset_id, preset in self.presets.by_ids(user_id, ids).items()
        }

    @staticmethod
    def _serialize(note: ResearchNote, preset_names: dict[int, str]) -> dict[str, Any]:
        return {
            "id": note.id,
            "ticker": note.ticker,
            "kind": note.kind,
            "title": note.title,
            "content": note.content,
            "preset_id": note.preset_id,
            "preset_name": preset_names.get(note.preset_id or -1),
            "is_resolved": note.is_resolved,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        }
