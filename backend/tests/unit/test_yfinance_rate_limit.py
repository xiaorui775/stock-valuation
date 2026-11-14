"""yfinance 限流异常分类测试（M2-16）：YFRateLimitError 应映射为 RateLimited。"""
from __future__ import annotations

import pytest

from app.providers.base import ProviderUnavailable, RateLimited
from app.providers.yfinance_provider import YFinanceProvider


class _FakeRateLimitError(Exception):
    pass


def _provider_with(rate_cls: type[Exception] | None) -> YFinanceProvider:
    p = YFinanceProvider()
    p._yf = object()  # 跳过真实 import
    p._rate_limit_error = rate_cls
    return p


def test_rate_limit_error_maps_to_rate_limited():
    p = _provider_with(_FakeRateLimitError)

    def boom():
        raise _FakeRateLimitError("Too Many Requests")

    with pytest.raises(RateLimited):
        p._wrap("行情获取失败")(boom)()


def test_other_error_maps_to_provider_unavailable():
    p = _provider_with(_FakeRateLimitError)

    def boom():
        raise ConnectionError("network down")

    with pytest.raises(ProviderUnavailable):
        p._wrap("行情获取失败")(boom)()


def test_no_rate_cls_all_errors_unavailable():
    p = _provider_with(None)

    def boom():
        raise _FakeRateLimitError("Too Many Requests")

    with pytest.raises(ProviderUnavailable):
        p._wrap("行情获取失败")(boom)()


def test_wrap_classifies_not_found_as_unavailable():
    """_wrap 不区分 TickerNotFound——外层 get_quote 的空数据分支才抛它。"""
    p = _provider_with(_FakeRateLimitError)

    def boom():
        raise LookupError("no data")

    with pytest.raises(ProviderUnavailable):
        p._wrap("行情获取失败")(boom)()
