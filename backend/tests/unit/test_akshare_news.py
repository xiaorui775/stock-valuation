"""A 股新闻与公告（M3-02）：akshare 解析的离线单测。

不联网：用假 DataFrame 模拟 akshare 返回，验证字段映射、
类型标注、公告失败时仅返回新闻、时间倒序。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import pytest

from app.providers.akshare_provider import AkshareProvider
from app.providers.base import ProviderUnavailable


def _news_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "新闻标题": "茅台发布三季报",
                "新闻链接": "https://example.com/a",
                "文章来源": "财联社",
                "发布时间": "2026-11-13 10:00:00",
            },
            {
                "新闻标题": "早间公告汇总",
                "新闻链接": "https://example.com/b",
                "文章来源": "证券时报网",
                "发布时间": "2026-11-14 08:30:00",
            },
            # 缺标题的行应被跳过
            {
                "新闻标题": None,
                "新闻链接": "https://example.com/c",
                "文章来源": "x",
                "发布时间": "2026-11-14 09:00:00",
            },
        ]
    )


def _disclosure_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "公告标题": "关于召开业绩说明会的公告",
                "公告链接": "https://example.com/d",
                "公告时间": "2026-11-12 19:00:00",
            }
        ]
    )


class _FakeAk:
    def stock_news_em(self, symbol: str) -> pd.DataFrame:
        assert symbol == "600519"
        return _news_df()

    def stock_zh_a_disclosure_report_cninfo(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return _disclosure_df()


def _provider_with(ak: Any) -> AkshareProvider:
    p = AkshareProvider()
    p._ak = ak
    return p


def test_news_and_announcement_mapped():
    p = _provider_with(_FakeAk())
    items = p.get_news("600519.SS")
    kinds = {i.kind for i in items}
    assert kinds == {"news", "announcement"}
    titles = [i.title for i in items]
    assert "茅台发布三季报" in titles
    assert "关于召开业绩说明会的公告" in titles


def test_news_sources_and_kind():
    p = _provider_with(_FakeAk())
    news = [i for i in p.get_news("600519.SS") if i.kind == "news"]
    assert {i.source for i in news} == {"财联社", "证券时报网"}


def test_news_sorted_desc_with_missing_last():
    p = _provider_with(_FakeAk())
    items = p.get_news("600519.SS")
    times = [i.published_at for i in items]
    known = [t for t in times if t is not None]
    assert known == sorted(known, reverse=True)
    assert all(
        items[i].published_at is not None or times[i + 1] is None if i + 1 < len(items) else True
        for i in range(len(items) - 1)
    )


def test_announcement_failure_returns_news_only():
    class _BrokenDisc:
        def stock_news_em(self, symbol: str) -> pd.DataFrame:
            return _news_df()

        def stock_zh_a_disclosure_report_cninfo(self, **kwargs) -> pd.DataFrame:
            raise RuntimeError("cninfo down")

    p = _provider_with(_BrokenDisc())
    items = p.get_news("600519.SS")
    assert {i.kind for i in items} == {"news"}
    assert len(items) == 2  # 两条有效新闻（缺标题的被跳过）


def test_news_upstream_failure_raises_unavailable():
    class _BrokenNews:
        def stock_news_em(self, symbol: str) -> pd.DataFrame:
            raise RuntimeError("em down")

    p = _provider_with(_BrokenNews())
    with pytest.raises(ProviderUnavailable):
        p.get_news("600519.SS")


def test_published_time_parsed():
    p = _provider_with(_FakeAk())
    items = p.get_news("600519.SS")
    target = next(i for i in items if i.title == "茅台发布三季报")
    assert target.published_at == datetime(2026, 11, 13, 10, 0, 0, tzinfo=UTC)
