"""缓存层测试。"""
from __future__ import annotations

import time

from app.providers.cache import TtlCache, cache_key


def test_set_and_get():
    cache = TtlCache()
    cache.set("k", {"a": 1}, ttl=60)
    entry = cache.get("k")
    assert entry is not None
    assert entry.value == {"a": 1}
    assert not entry.is_expired


def test_expired_entry_is_marked():
    cache = TtlCache()
    cache.set("k", 1, ttl=0)
    time.sleep(0.01)
    entry = cache.get("k")
    assert entry is not None
    assert entry.is_expired


def test_missing_key_returns_none():
    assert TtlCache().get("nope") is None


def test_delete_and_clear():
    cache = TtlCache()
    cache.set("a", 1, 60)
    cache.set("b", 2, 60)
    cache.delete("a")
    assert cache.get("a") is None
    assert cache.clear() == 1
    assert cache.get("b") is None


def test_cache_key_joins_parts():
    assert cache_key("quote", "AAPL") == "quote:AAPL"
    assert cache_key("history", "AAPL", "1y", "1d") == "history:AAPL:1y:1d"
