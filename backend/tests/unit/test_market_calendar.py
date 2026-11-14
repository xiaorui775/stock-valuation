"""交易时段与 52 周位置单元测试。"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.providers.models import Market
from app.services.market_calendar import (
    next_trading_day,
    session_status,
    week52_position,
)


def _at(market_tz: str, hh: int, mm: int, weekday: int = 2) -> datetime:
    """构造某市场当地时间对应的 UTC 时间。

    `weekday` 用 Python 的 weekday 编号（0=周一，4=周五）。
    基准周为 2026-03-02（周一）。
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    base = datetime(2026, 3, 2, tzinfo=ZoneInfo(market_tz))
    local = base + timedelta(days=weekday, hours=hh, minutes=mm)
    return local.astimezone(UTC)


def test_us_regular_session():
    s = session_status(Market.US, now=_at("America/New_York", 10, 30))
    assert s.status == "regular"
    assert s.label == "盘中"
    assert s.is_open is True


def test_us_pre_market():
    s = session_status(Market.US, now=_at("America/New_York", 7, 0))
    assert s.label == "盘前"
    assert s.is_open is False


def test_us_after_hours():
    s = session_status(Market.US, now=_at("America/New_York", 17, 0))
    assert s.label == "盘后"


def test_us_closed_outside_hours():
    s = session_status(Market.US, now=_at("America/New_York", 22, 0))
    assert s.label == "休市"


def test_weekend_is_closed():
    s = session_status(Market.US, now=_at("America/New_York", 11, 0, weekday=5))
    assert s.label == "休市"
    assert s.note == "周末休市"


def test_cn_session():
    s = session_status(Market.CN, now=_at("Asia/Shanghai", 10, 0))
    assert s.label == "盘中"


def test_cn_lunch_break_is_closed():
    """A 股 11:30–13:00 午休，按已收盘处理。"""
    s = session_status(Market.CN, now=_at("Asia/Shanghai", 12, 0))
    assert s.label != "盘中"


def test_hk_session():
    s = session_status(Market.HK, now=_at("Asia/Hong_Kong", 11, 0))
    assert s.label == "盘中"


def test_unknown_market_is_closed():
    s = session_status(Market.UNKNOWN)
    assert s.label == "休市"
    assert s.note is not None


def test_session_reports_local_time():
    s = session_status(Market.US, now=_at("America/New_York", 10, 30))
    assert s.local_time == "2026-03-04 10:30"
    assert s.timezone == "America/New_York"


def test_week52_position_midpoint():
    r = week52_position(150.0, 200.0, 100.0)
    assert r["position"] == pytest.approx(0.5)
    assert r["from_high_pct"] == pytest.approx(-25.0)
    assert r["from_low_pct"] == pytest.approx(50.0)


def test_week52_position_at_high():
    r = week52_position(200.0, 200.0, 100.0)
    assert r["position"] == pytest.approx(1.0)


def test_week52_position_missing_inputs_return_none():
    r = week52_position(None, 200.0, 100.0)
    assert r["position"] is None
    assert r["from_high_pct"] is None


def test_week52_position_invalid_range():
    r = week52_position(150.0, 100.0, 100.0)
    assert r["position"] is None


def test_next_trading_day_skips_weekend():
    # 2026-03-06 是周五（weekday=4）
    d = next_trading_day(Market.US, now=_at("America/New_York", 11, 0, weekday=4))
    assert d == "2026-03-09"
