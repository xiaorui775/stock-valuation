"""新闻去重服务单测（FR-NEWS-03）。"""
from __future__ import annotations

from datetime import datetime

from app.providers.models import NewsItem
from app.services.news_service import dedupe_news


def _item(title: str, url: str | None, published: str | None, kind: str = "news") -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        kind=kind,
        published_at=datetime.fromisoformat(published) if published else None,
    )


def test_dedupe_by_url_keeps_latest():
    items = [
        _item("标题A", "http://x/1", "2026-11-14T09:00:00"),
        _item("标题A", "http://x/1", "2026-11-14T09:00:00"),
    ]
    assert len(dedupe_news(items)) == 1


def test_dedupe_by_url_keeps_newer():
    old = _item("旧标题", "http://x/1", "2026-11-13T09:00:00")
    new = _item("新标题", "http://x/1", "2026-11-14T09:00:00")
    out = dedupe_news([old, new])
    assert len(out) == 1
    assert out[0] is new


def test_dedupe_by_title_time_without_url():
    items = [
        _item("无链接", None, "2026-11-14T09:00:00"),
        _item("无链接", None, "2026-11-14T09:00:00"),
    ]
    assert len(dedupe_news(items)) == 1


def test_dedupe_empty():
    assert dedupe_news([]) == []


def test_dedupe_different_urls_kept():
    items = [
        _item("甲", "http://x/1", "2026-11-14T09:00:00"),
        _item("乙", "http://x/2", "2026-11-14T09:00:00"),
    ]
    assert len(dedupe_news(items)) == 2
