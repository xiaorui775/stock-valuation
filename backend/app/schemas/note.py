"""研究笔记接口模型（FR-RESEARCH-03）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

NoteKind = Literal["conclusion", "assumption", "question", "note"]

NOTE_KINDS: tuple[str, ...] = ("conclusion", "assumption", "question", "note")


class NoteCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    kind: NoteKind = "note"
    title: str = Field(min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=5000)
    preset_id: int | None = None
    is_resolved: bool = False

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("笔记标题不能为空")
        return cleaned


class NoteUpdate(BaseModel):
    kind: NoteKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=5000)
    preset_id: int | None = None
    is_resolved: bool | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("笔记标题不能为空")
        return cleaned


class NoteOut(BaseModel):
    id: int
    ticker: str
    kind: str
    title: str
    content: str | None = None
    preset_id: int | None = None
    preset_name: str | None = None
    is_resolved: bool = False
    created_at: datetime
    updated_at: datetime


class NoteListOut(BaseModel):
    items: list[NoteOut]
    total: int = 0
