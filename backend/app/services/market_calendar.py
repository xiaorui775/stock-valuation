"""交易时段判断：盘前 / 盘中 / 盘后 / 休市。

只做粗粒度判断，不含节假日日历——节假日会落在「休市」之外的情形，
因此结果标注为参考值，不作为行情延迟的准确依据。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.providers.models import Market

# 各市场的常规交易时段（当地时间，24 小时制）
# pre_open / regular_open / regular_close / post_close
SESSIONS: dict[str, dict[str, time]] = {
    Market.US.value: {
        "pre_open": time(4, 0),
        "regular_open": time(9, 30),
        "regular_close": time(16, 0),
        "post_close": time(20, 0),
    },
    Market.HK.value: {
        "pre_open": time(9, 0),
        "regular_open": time(9, 30),
        "regular_close": time(16, 0),
        "post_close": time(16, 10),
    },
    Market.CN.value: {
        "pre_open": time(9, 15),
        "regular_open": time(9, 30),
        "regular_close": time(15, 0),
        "post_close": time(15, 30),
    },
}

# 午休时段：A 股 11:30–13:00 不连续交易
LUNCH_BREAKS: dict[str, tuple[time, time]] = {
    Market.CN.value: (time(11, 30), time(13, 0)),
}

TIMEZONES: dict[str, str] = {
    Market.US.value: "America/New_York",
    Market.HK.value: "Asia/Hong_Kong",
    Market.CN.value: "Asia/Shanghai",
}

# 周六周日
_WEEKEND = (5, 6)


@dataclass(frozen=True)
class SessionStatus:
    """交易时段状态。"""

    status: str
    """pre / regular / post / closed"""

    label: str
    """盘前 / 盘中 / 盘后 / 休市"""

    timezone: str
    local_time: str
    note: str | None = None

    @property
    def is_open(self) -> bool:
        return self.status == "regular"


def session_status(
    market: Market | str,
    now: datetime | None = None,
) -> SessionStatus:
    """判断某市场当前处于哪个交易时段。

    `now` 必须是带时区的 datetime；缺省用当前 UTC 时间。
    """
    market_value = market.value if isinstance(market, Market) else str(market)
    tz_name = TIMEZONES.get(market_value, "UTC")
    tz = ZoneInfo(tz_name)

    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    local = moment.astimezone(tz)

    session = SESSIONS.get(market_value)
    if session is None:
        return SessionStatus(
            status="closed",
            label="休市",
            timezone=tz_name,
            local_time=local.strftime("%Y-%m-%d %H:%M"),
            note="未知市场，无常规交易时段定义",
        )

    if local.weekday() in _WEEKEND:
        return SessionStatus(
            status="closed",
            label="休市",
            timezone=tz_name,
            local_time=local.strftime("%Y-%m-%d %H:%M"),
            note="周末休市",
        )

    now_t = local.time()
    lunch = LUNCH_BREAKS.get(market_value)

    if now_t < session["pre_open"]:
        label, note = "休市", "开盘前时段"
    elif now_t < session["regular_open"]:
        label, note = "盘前", None
    elif lunch and lunch[0] <= now_t < lunch[1]:
        label, note = "休市", "午间休市"
    elif lunch and now_t >= lunch[1] and now_t < session["regular_close"] or now_t < session["regular_close"]:
        label, note = "盘中", None
    elif now_t < session["post_close"]:
        label, note = "盘后", None
    else:
        label, note = "休市", "已收盘"

    status = {
        "盘前": "pre",
        "盘中": "regular",
        "盘后": "post",
        "休市": "closed",
    }[label]

    return SessionStatus(
        status=status,
        label=label,
        timezone=tz_name,
        local_time=local.strftime("%Y-%m-%d %H:%M"),
        note=note,
    )


def week52_position(
    price: float | None,
    high: float | None,
    low: float | None,
) -> dict[str, float | None]:
    """现价在 52 周区间中的位置（0–1），以及距高低点的幅度。

    缺少现价或区间端点时全部返回 None——不做估算填充。
    """
    if price is None or high is None or low is None:
        return {"position": None, "from_high_pct": None, "from_low_pct": None}
    if high <= low:
        return {"position": None, "from_high_pct": None, "from_low_pct": None}
    position = (price - low) / (high - low)
    return {
        "position": position,
        "from_high_pct": (price - high) / high * 100,
        "from_low_pct": (price - low) / low * 100 if low else None,
    }


def market_day(market: Market | str, now: datetime | None = None) -> str:
    """交易所时区的自然日（YYYY-MM-DD）。"""
    market_value = market.value if isinstance(market, Market) else str(market)
    tz = ZoneInfo(TIMEZONES.get(market_value, "UTC"))
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(tz).date().isoformat()


def days_until(
    target: date, market: Market | str, now: datetime | None = None
) -> int | None:
    """距目标日期的自然日数；目标日期已过返回 None（不做负数展示）。"""
    today = date.fromisoformat(market_day(market, now))
    remaining = (target - today).days
    return remaining if remaining >= 0 else None


def next_trading_day(market: Market | str, now: datetime | None = None) -> str | None:
    """粗略给出下一个交易日的日期（不含节假日判断）。"""

    market_value = market.value if isinstance(market, Market) else str(market)
    tz = ZoneInfo(TIMEZONES.get(market_value, "UTC"))
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    local = moment.astimezone(tz)
    day = local.date()
    for _ in range(7):
        day += timedelta(days=1)
        if day.weekday() not in _WEEKEND:
            return day.isoformat()
    return None
