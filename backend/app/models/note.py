"""研究笔记：按标的记录结论、假设与待验证问题（FR-RESEARCH-03）。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ResearchNote(Base, TimestampMixin):
    __tablename__ = "research_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # conclusion | assumption | question | note
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="note")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 可选关联到同标的的估值预设；预设删除时置空，不连带删除笔记
    preset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("valuation_presets.id", ondelete="SET NULL"), nullable=True
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_research_notes_user_ticker", "user_id", "ticker"),
    )
