"""概览服务：组装报价头、交易时段、52 周位置与估值结论。

对应 PRD §5.3。
"""
from __future__ import annotations

from typing import Any, Optional

from app.providers.models import Quote
from app.services.market_calendar import session_status, week52_position
from app.services.market_service import MarketService
from app.services.valuation_service import ValuationService


class OverviewService:
    def __init__(
        self,
        market_service: Optional[MarketService] = None,
        valuation_service: Optional[ValuationService] = None,
    ) -> None:
        self.market = market_service or MarketService()

    # ------------------------------------------------------------------
    def build(self, ticker: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """返回 (概览数据, meta)。"""
        quote, meta = self.market.get_quote(ticker)

        session = session_status(quote.market)
        w52 = week52_position(quote.price, quote.week52_high, quote.week52_low)

        conclusion = self._conclusion(quote)

        from app.core.tickers import market_label

        data = {
            "ticker": quote.ticker,
            "name": quote.name,
            "market": quote.market,
            "market_label": market_label(quote.market),
            "currency": quote.currency,
            "price": quote.price,
            "change": quote.change,
            "change_pct": quote.change_pct,
            "session": {
                "status": session.status,
                "label": session.label,
                "timezone": session.timezone,
                "local_time": session.local_time,
                "note": session.note,
            },
            "week52": w52,
            "conclusion": conclusion,
            "quote": quote.model_dump(),
            "as_of": quote.as_of,
        }
        return data, meta

    # ------------------------------------------------------------------
    def _conclusion(self, quote: Quote) -> Optional[dict[str, Any]]:
        """估值结论：DCF 每股价值 + 综合判定。

        缺少财务数据时返回 None，界面显示「—」而不是 0。
        """
        try:
            financials = self.market.get_financials(quote.ticker)[0]
        except Exception:
            return None

        if not financials.years:
            return None

        result = ValuationService(quote, financials).build()
        dcf = result.get("dcf") or {}
        summary = result.get("summary") or {}
        if not dcf and not summary:
            return None

        return {
            "dcf_per_share": dcf.get("per_share"),
            "upside_pct": dcf.get("upside_pct"),
            "average_value": summary.get("average_value"),
            "vs_price_pct": summary.get("vs_price_pct"),
            "band": summary.get("band"),
            "methods_used": summary.get("methods_used", 0),
            "note": summary.get("note"),
        }
