"""估值预设：按用户与标的存在的一组假设（FR-VAL-07）。"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ValuationPreset(Base, TimestampMixin):
    __tablename__ = "valuation_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_valuation_presets_user_ticker_name", "user_id", "ticker", "name", unique=True),
    )
