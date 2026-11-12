"""缓存层：L1 进程内 TTL + L2 SQLite 持久化。

L1 用于行情/历史/新闻等高频数据；L2 用于财务报表/元数据等慢变数据。
过期数据允许 stale 返回（标记 stale=true），同时触发后台刷新。
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import Session as OrmSession

from app.models.base import Base, utcnow


@dataclass
class CacheEntry:
    value: Any
    fetched_at: float
    expires_at: float

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    @property
    def age(self) -> float:
        return time.time() - self.fetched_at


class TtlCache:
    """线程安全的进程内 TTL 缓存。"""

    def __init__(self) -> None:
        self._data: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._data.get(key)
        if entry is None:
            return None
        return entry

    def set(self, key: str, value: Any, ttl: int) -> CacheEntry:
        now = time.time()
        entry = CacheEntry(value=value, fetched_at=now, expires_at=now + ttl)
        with self._lock:
            self._data[key] = entry
        return entry

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> int:
        with self._lock:
            count = len(self._data)
            self._data.clear()
            return count

    def prune(self) -> int:
        """清理过期且超过保留期的条目。"""
        now = time.time()
        with self._lock:
            stale = [k for k, e in self._data.items() if now - e.fetched_at > 86400]
            for k in stale:
                self._data.pop(k, None)
        return len(stale)


class DataCache(Base):
    """L2 持久化缓存表。"""

    __tablename__ = "data_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)  # type: ignore[name-defined]
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    fetched_at: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)


class PersistentCache:
    """SQLite 支撑的 L2 缓存。"""

    def __init__(self, db: OrmSession) -> None:
        self.db = db

    def get(self, key: str) -> Optional[CacheEntry]:
        row = self.db.scalar(select(DataCache).where(DataCache.key == key))
        if row is None:
            return None
        try:
            value = json.loads(row.payload_json)
        except json.JSONDecodeError:
            return None
        return CacheEntry(value=value, fetched_at=row.fetched_at, expires_at=row.expires_at)

    def set(self, key: str, value: Any, ttl: int, source: str = "") -> CacheEntry:
        now = int(time.time())
        payload = json.dumps(value, ensure_ascii=False, default=str)
        row = self.db.get(DataCache, key)
        if row is None:
            row = DataCache(key=key, payload_json=payload, source=source, fetched_at=now, expires_at=now + ttl)
            self.db.add(row)
        else:
            row.payload_json = payload
            row.source = source
            row.fetched_at = now
            row.expires_at = now + ttl
        self.db.flush()
        return CacheEntry(value=value, fetched_at=now, expires_at=now + ttl)

    def delete(self, key: str) -> None:
        row = self.db.get(DataCache, key)
        if row is not None:
            self.db.delete(row)
            self.db.flush()

    def clear(self) -> int:
        rows = self.db.scalars(select(DataCache)).all()
        count = len(rows)
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        return count

    def prune(self, max_age_seconds: int = 86400 * 7) -> int:
        cutoff = int(time.time()) - max_age_seconds
        rows = self.db.scalars(
            select(DataCache).where(DataCache.fetched_at < cutoff)
        ).all()
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        return len(rows)


# 全局 L1 缓存
l1_cache = TtlCache()


def cache_key(*parts: Any) -> str:
    return ":".join(str(p) for p in parts)


def now_ts() -> int:
    return int(time.time())


def iso_now():
    return utcnow().isoformat()


__all__ = [
    "CacheEntry",
    "DataCache",
    "PersistentCache",
    "TtlCache",
    "cache_key",
    "iso_now",
    "l1_cache",
    "now_ts",
]
