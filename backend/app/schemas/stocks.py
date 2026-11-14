"""行情、财务、新闻接口的响应模型。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.providers.models import Instrument, InstrumentKind, Market


class QuoteOut(BaseModel):
    ticker: str
    name: str
    currency: str | None = None
    market: Market = Market.UNKNOWN
    price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    open_price: float | None = None
    market_cap: float | None = None
    pe_ttm: float | None = None
    forward_pe: float | None = None
    eps_ttm: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    week52_high: float | None = None
    week52_low: float | None = None
    volume: float | None = None
    shares_outstanding: float | None = None
    price_to_book: float | None = None
    price_to_sales: float | None = None
    ev_ebitda: float | None = None
    peg: float | None = None
    total_debt: float | None = None
    total_cash: float | None = None
    total_revenue: float | None = None
    ebitda: float | None = None
    book_value_per_share: float | None = None
    as_of: datetime | None = None

    model_config = {"from_attributes": True}


class CalendarOut(BaseModel):
    """财报日历（仅展示，不做提醒/推送）。"""

    ticker: str
    earnings_date: date | None = None
    dividend_date: date | None = None
    ex_dividend_date: date | None = None
    days_until_earnings: int | None = None
    note: str | None = None


class BarOut(BaseModel):
    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: float | None = None

    model_config = {"from_attributes": True}


class IndicatorsOut(BaseModel):
    """随历史行情返回的技术指标序列（FR-CHART-03）。

    每个序列与 `bars` 按下标对齐；窗口不满的位置为 None，前端渲染为缺省。
    """

    ma5: list[float | None] = Field(default_factory=list)
    ma10: list[float | None] = Field(default_factory=list)
    ma20: list[float | None] = Field(default_factory=list)
    ma60: list[float | None] = Field(default_factory=list)
    ma120: list[float | None] = Field(default_factory=list)
    boll_mid: list[float | None] = Field(default_factory=list)
    boll_upper: list[float | None] = Field(default_factory=list)
    boll_lower: list[float | None] = Field(default_factory=list)
    dif: list[float | None] = Field(default_factory=list)
    dea: list[float | None] = Field(default_factory=list)
    macd: list[float | None] = Field(default_factory=list)
    rsi14: list[float | None] = Field(default_factory=list)


class HistoryOut(BaseModel):
    ticker: str
    period: str
    interval: str
    adjustment: str = "前复权"
    """复权方式。数据源按最新价调整历史价格时即为前复权。"""
    start_date: date | None = None
    end_date: date | None = None
    count: int = 0
    bars: list[BarOut]
    indicators: IndicatorsOut = Field(default_factory=IndicatorsOut)


class FinancialYearOut(BaseModel):
    year: int
    period_end: date | None = None
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None
    free_cash_flow: float | None = None
    total_debt: float | None = None
    total_cash: float | None = None
    total_equity: float | None = None
    shares_outstanding: float | None = None
    accounts_receivable: float | None = None
    inventory: float | None = None
    yoy: dict[str, float | None] = {}
    """各科目相对上一财年的同比（百分点），无上期或上期为 0 时为 null。"""

    model_config = {"from_attributes": True}


class CrossCheckOut(BaseModel):
    """数据源交叉校验结果（FR-DATA-04）。"""

    field: str
    values: dict[str, float]
    ratio: float | None = None
    diff_pct: float
    conflict: bool
    note: str

class FinancialsOut(BaseModel):
    ticker: str
    currency: str | None = None
    period: str
    years: list[FinancialYearOut]
    cagr: dict[str, float | None] = {}
    """最新一期相对 3 年前的复合年均增长率（百分点）。"""
    cagr_years: int = 3
    missing_fields: list[str] = []
    """所有财年都缺失的科目名。"""
    cross_check: CrossCheckOut | None = None
    """A 股营业收入年报 vs TTM 交叉校验；仅主源为 akshare 且两侧都有值时返回。"""


class NewsItemOut(BaseModel):
    title: str
    url: str | None = None
    source: str | None = None
    kind: str
    published_at: datetime | None = None
    summary: str | None = None

    model_config = {"from_attributes": True}


class NewsListOut(BaseModel):
    ticker: str
    items: list[NewsItemOut]


class InstrumentOut(BaseModel):
    ticker: str
    name: str
    market: Market = Market.UNKNOWN
    exchange: str | None = None
    currency: str | None = None
    kind: InstrumentKind = InstrumentKind.UNKNOWN
    provider: str | None = None
    note: str | None = None
    """给用户的提示，例如 A 股代码需要补交易所后缀。"""

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _lift_note(cls, value: Any) -> Any:
        """把 Instrument.source_meta 里的 note 提到顶层。"""
        if isinstance(value, Instrument):
            meta = value.source_meta or {}
            note = meta.get("note")
            if note:
                data = value.model_dump()
                data["note"] = note
                return data
        return value


class SessionOut(BaseModel):
    """交易时段状态。"""

    status: str
    label: str
    timezone: str
    local_time: str
    note: str | None = None


class Week52PositionOut(BaseModel):
    """现价在 52 周区间中的位置。"""

    position: float | None = None
    from_high_pct: float | None = None
    from_low_pct: float | None = None


class ValuationConclusionOut(BaseModel):
    """概览页的估值结论卡（FR-OVERVIEW-04）。"""

    dcf_per_share: float | None = None
    upside_pct: float | None = None
    average_value: float | None = None
    vs_price_pct: float | None = None
    band: str | None = None
    methods_used: int = 0
    note: str | None = None


class OverviewOut(BaseModel):
    """个股概览聚合（FR-OVERVIEW-01 ~ 04）。"""

    ticker: str
    name: str
    market: Market = Market.UNKNOWN
    market_label: str = "未知"
    currency: str | None = None
    price: float | None = None
    change: float | None = None
    change_pct: float | None = None
    session: SessionOut | None = None
    week52: Week52PositionOut | None = None
    conclusion: ValuationConclusionOut | None = None
    quote: QuoteOut | None = None
    """完整行情快照，供关键指标区块使用。"""
    as_of: datetime | None = None


class DataQualitySectionOut(BaseModel):
    key: str
    label: str
    source: str | None = None
    as_of: datetime | None = None
    cached: bool = False
    stale: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    note: str | None = None


class DataQualityOut(BaseModel):
    """个股数据质量汇总（FR-RESEARCH-05）：只描述取数状态，不推算数据。"""

    ticker: str
    checked_at: datetime
    sections: list[DataQualitySectionOut]
    warnings: list[str] = Field(default_factory=list)
    cross_check: CrossCheckOut | None = None
