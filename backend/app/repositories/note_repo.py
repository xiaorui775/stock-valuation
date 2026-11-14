"""研究笔记的数据访问（FR-RESEARCH-03）。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as OrmSession

from app.models.note import ResearchNote


class ResearchNoteRepository:
    def __init__(self, db: OrmSession) -> None:
        self.db = db

    def list_for(
        self,
        user_id: int,
        ticker: Optional[str] = None,
        query: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> list[ResearchNote]:
        stmt = select(ResearchNote).where(ResearchNote.user_id == user_id)
        if ticker:
            stmt = stmt.where(ResearchNote.ticker == ticker)
        if kind:
            stmt = stmt.where(ResearchNote.kind == kind)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    ResearchNote.title.ilike(pattern),
                    ResearchNote.content.ilike(pattern),
                )
            )
        stmt = stmt.order_by(
            ResearchNote.updated_at.desc(), ResearchNote.id.desc()
        )
        return list(self.db.scalars(stmt))

    def get(self, user_id: int, note_id: int) -> Optional[ResearchNote]:
        return self.db.scalar(
            select(ResearchNote).where(
                ResearchNote.id == note_id,
                ResearchNote.user_id == user_id,
            )
        )

    def add(self, note: ResearchNote) -> ResearchNote:
        self.db.add(note)
        self.db.flush()
        return note

    def delete(self, note: ResearchNote) -> None:
        self.db.delete(note)
        self.db.flush()
