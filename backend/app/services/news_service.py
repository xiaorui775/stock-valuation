"""新闻去重服务（FR-NEWS-03）：按 URL 与 标题+时间 去重，同键保留较新条目。"""
from __future__ import annotations

from app.providers.models import NewsItem


def _title_key(item: NewsItem) -> str:
    return f"{(item.title or '').strip()}|{item.published_at.isoformat() if item.published_at else ''}"


def _newer(a: NewsItem, b: NewsItem) -> bool:
    if a.published_at is None and b.published_at is None:
        return False  # 同键、均无时间：保留先出现的一条
    if a.published_at is None:
        return False
    if b.published_at is None:
        return True
    return a.published_at > b.published_at


def dedupe_news(items: list[NewsItem]) -> list[NewsItem]:
    """按 URL 与 标题+时间 去重；重复时保留发布时间较晚的一条。"""
    url_rep: dict[str, NewsItem] = {}
    title_rep: dict[str, NewsItem] = {}
    for item in items:
        url = (item.url or "").strip()
        if url:
            prev = url_rep.get(url)
            if prev is None or _newer(item, prev):
                url_rep[url] = item
        tk = _title_key(item)
        prev = title_rep.get(tk)
        if prev is None or _newer(item, prev):
            title_rep[tk] = item

    # 先按 URL 去重（保留 url_rep 选中的），再按标题去重（保留 title_rep 选中的）
    out: list[NewsItem] = []
    seen_title: set[str] = set()
    for item in items:
        url = (item.url or "").strip()
        if url and url_rep.get(url) is not item:
            continue
        tk = _title_key(item)
        if title_rep.get(tk) is not item:
            continue
        if tk in seen_title and not url:
            continue
        seen_title.add(tk)
        out.append(item)
    return out
