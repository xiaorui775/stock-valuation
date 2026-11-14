"""代码规范化与市场识别单元测试。"""
from __future__ import annotations

import pytest

from app.core.tickers import (
    exchange_hint,
    is_code_like,
    market_label,
    normalize_ticker,
    parse_ticker,
)
from app.providers.models import Market


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("aapl", "AAPL"),
        ("  msft  ", "MSFT"),
        ("0700.hk", "0700.HK"),
        ("600519.ss", "600519.SS"),
    ],
)
def test_normalize_ticker(raw, expected):
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize(
    ("ticker", "market"),
    [
        ("AAPL", Market.US),
        ("MSFT", Market.US),
        ("0700.HK", Market.HK),
        ("9988.HK", Market.HK),
        ("600519.SS", Market.CN),
        ("000001.SZ", Market.CN),
        ("830799.BJ", Market.CN),
    ],
)
def test_detect_market_by_suffix(ticker, market):
    assert parse_ticker(ticker).market is market


def test_parse_ticker_suggests_cn_suffix_for_bare_code():
    info = parse_ticker("600519")
    assert info.ticker == "600519"
    assert info.market is Market.CN
    assert info.needs_suffix is True
    assert info.suffix_suggestion == ".SS"


def test_parse_ticker_suggests_sz_suffix():
    assert parse_ticker("000001").suffix_suggestion == ".SZ"


def test_parse_ticker_suggests_bj_suffix():
    assert parse_ticker("830799").suffix_suggestion == ".BJ"


def test_parse_ticker_with_suffix_needs_no_hint():
    info = parse_ticker("600519.SS")
    assert info.needs_suffix is False
    assert info.suffix_suggestion is None


def test_parse_ticker_empty():
    info = parse_ticker("   ")
    assert info.ticker == ""
    assert info.market is Market.UNKNOWN


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AAPL", True),
        ("600519", True),
        ("600519.SS", True),
        ("BRK.B", True),
        ("苹果", False),
        ("Apple Inc", False),
        ("", False),
    ],
)
def test_is_code_like(raw, expected):
    assert is_code_like(raw) is expected


def test_exchange_hint():
    assert exchange_hint("600519.SS") == "上交所"
    assert exchange_hint("000001.SZ") == "深交所"
    assert exchange_hint("830799.BJ") == "北交所"
    assert exchange_hint("0700.HK") == "港交所"
    assert exchange_hint("AAPL") is None


def test_market_label():
    assert market_label(Market.US) == "美股"
    assert market_label(Market.HK) == "港股"
    assert market_label(Market.CN) == "A股"
    assert market_label(Market.UNKNOWN) == "未知"
