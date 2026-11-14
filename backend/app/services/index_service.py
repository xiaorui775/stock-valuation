"""预设指数成分股：内置快照 + 数据源刷新（§5.11 FR-SCR-01 / Q11）。

成分股名单会随指数调整变化，所以：
- 首次访问用内置快照播种，并把 `updated_at` 设成快照日期（不是「现在」，避免假装新鲜）；
- 刷新时如果数据源没有这个能力，保留现有名单并如实说明原因，不清空、不编造。
"""
from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.models.screener import IndexConstituent
from app.providers.index_members import (
    INDEX_LABELS,
    INDEX_SNAPSHOTS,
    SNAPSHOT_DATE,
    SNAPSHOT_SOURCE,
)
from app.repositories.screener_repo import IndexRepository
from app.services.market_service import MarketService


class IndexService:
    def __init__(self, db: OrmSession, market: MarketService | None = None) -> None:
        self.db = db
        self.repo = IndexRepository(db)
        self.market = market or MarketService()

    def list(self) -> list[dict[str, Any]]:
        return [self._summary(key) for key in INDEX_LABELS]

    def get(self, key: str) -> dict[str, Any]:
        rows = self._ensure(key)
        source = rows[0].source if rows else SNAPSHOT_SOURCE
        return {
            "key": key,
            "label": INDEX_LABELS[key],
            "count": len(rows),
            "source": source,
            "updated_at": _latest(rows),
            "members": [{"ticker": row.ticker, "name": row.name} for row in rows],
        }

    def tickers(self, key: str) -> list[str]:
        return [row.ticker for row in self._ensure(key)]

    def refresh(self, key: str) -> dict[str, Any]:
        self._require_key(key)
        try:
            members, meta = self.market.get_index_members(key)
        except AppError as exc:
            rows = self._ensure(key)
            return {
                "key": key,
                "label": INDEX_LABELS[key],
                "refreshed": False,
                "reason": exc.message,
                "count": len(rows),
                "source": rows[0].source if rows else SNAPSHOT_SOURCE,
                "updated_at": _latest(rows),
            }

        rows = self.repo.replace(
            key,
            [(item.ticker, item.name) for item in members],
            source=(meta.get("source") or "provider"),
        )
        self.db.commit()
        return {
            "key": key,
            "label": INDEX_LABELS[key],
            "refreshed": True,
            "reason": None,
            "count": len(rows),
            "source": rows[0].source if rows else "",
            "updated_at": _latest(rows),
        }

    # ------------------------------------------------------------------
    def _summary(self, key: str) -> dict[str, Any]:
        rows = self._ensure(key)
        return {
            "key": key,
            "label": INDEX_LABELS[key],
            "count": len(rows),
            "source": rows[0].source if rows else SNAPSHOT_SOURCE,
            "updated_at": _latest(rows),
        }

    def _ensure(self, key: str) -> list[IndexConstituent]:
        self._require_key(key)
        rows = self.repo.list(key)
        if rows:
            return rows
        seeded_at = datetime.combine(SNAPSHOT_DATE, time.min, tzinfo=UTC)
        rows = self.repo.replace(
            key,
            [(ticker, "") for ticker in INDEX_SNAPSHOTS[key]],
            source=SNAPSHOT_SOURCE,
        )
        for row in rows:
            row.created_at = seeded_at
            row.updated_at = seeded_at
        self.db.commit()
        return rows

    @staticmethod
    def _require_key(key: str) -> None:
        if key not in INDEX_LABELS:
            raise AppError(
                ErrorCode.NOT_FOUND,
                f"未知的预设指数 {key}，可选 {'/'.join(INDEX_LABELS)}",
                404,
            )


def _latest(rows: list[IndexConstituent]) -> datetime | None:
    return max((row.updated_at for row in rows if row.updated_at), default=None)
