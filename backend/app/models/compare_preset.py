"""常用对比组合（FR-RESEARCH-06）。"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ComparePreset(Base, TimestampMixin):
    __tablename__ = "compare_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    tickers_json: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_compare_presets_user_name", "user_id", "name", unique=True),
    )
