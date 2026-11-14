"""个股数据质量汇总（PRD §5.17 FR-RESEARCH-05）。

聚合行情、财务报表、新闻与财报日历的取数状态：来源、时间、缓存/stale、
缺失字段与交叉校验差异，帮助用户判断当前结论的可信度。只汇总已有结果，
不额外推算数据。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from app.core.errors import AppError
from app.core.tickers import normalize_ticker
from app.services.financials_service import FinancialsService
from app.services.market_service import MarketService


class DataQualityService:
    def __init__(self, market: MarketService | None = None) -> None:
        self.market = market if market is not None else MarketService()

    def build(self, ticker: str) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        sections: list[dict[str, Any]] = []
        cross_check: Optional[dict[str, Any]] = None

        # ---- 行情 ----
        try:
            quote, meta = self.market.get_quote(ticker)
            sections.append(
                self._section(
                    "quote",
                    "行情快照",
                    meta,
                    missing=quote.missing_fields,
                )
            )
        except AppError as exc:
            if exc.status_code == 404:
                raise
            sections.append(self._unavailable("quote", "行情快照", exc.message))

        # ---- 财务报表 ----
        try:
            view, meta = FinancialsService(self.market).get(ticker)
            cross_check = view.get("cross_check")
            note = None
            if cross_check and cross_check.get("conflict"):
                note = "年报营收与 TTM 营收差异较大，已标记为「数据源存在差异」"
            sections.append(
                self._section(
                    "financials",
                    "年度财务报表",
                    meta,
                    missing=view.get("missing_fields") or [],
                    note=note,
                )
            )
        except AppError as exc:
            if exc.status_code == 404:
                raise
            sections.append(self._unavailable("financials", "年度财务报表", exc.message))

        # ---- 新闻与公告 ----
        try:
            items, meta = self.market.get_news(ticker)
            sections.append(
                self._section(
                    "news",
                    "新闻与公告",
                    meta,
                    note=f"本次返回 {len(items)} 条",
                )
            )
        except AppError as exc:
            if exc.status_code == 404:
                raise
            sections.append(self._unavailable("news", "新闻与公告", exc.message))

        # ---- 财报日历 ----
        try:
            calendar, meta = self.market.get_calendar(ticker)
            if calendar is None:
                note = "数据源未提供财报日历"
            elif calendar.earnings_date is None:
                note = "数据源未提供下一次财报日"
            else:
                note = f"下一次财报：{calendar.earnings_date.isoformat()}"
            sections.append(
                self._section("calendar", "财报日历", meta, note=note)
            )
        except AppError as exc:
            if exc.status_code == 404:
                raise
            sections.append(self._unavailable("calendar", "财报日历", exc.message))

        return {
            "ticker": ticker,
            "checked_at": datetime.now(UTC),
            "sections": sections,
            "warnings": self._warnings(sections, cross_check),
            "cross_check": cross_check,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _section(
        key: str,
        label: str,
        meta: dict[str, Any],
        missing: Optional[list[str]] = None,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "source": meta.get("source"),
            "as_of": meta.get("as_of"),
            "cached": bool(meta.get("cached")),
            "stale": bool(meta.get("stale")),
            "missing_fields": list(missing or []),
            "note": note,
        }

    @staticmethod
    def _unavailable(key: str, label: str, reason: str) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "source": None,
            "as_of": None,
            "cached": False,
            "stale": False,
            "missing_fields": [],
            "note": f"数据不可用：{reason}",
        }

    @staticmethod
    def _warnings(
        sections: list[dict[str, Any]],
        cross_check: Optional[dict[str, Any]],
    ) -> list[str]:
        warnings: list[str] = []
        for section in sections:
            if section["stale"]:
                warnings.append(f"{section['label']}返回的是过期缓存，数据可能不是最新")
            if section["missing_fields"]:
                fields = "、".join(section["missing_fields"])
                warnings.append(f"{section['label']}缺失字段：{fields}")
            if section["source"] is None and section["note"]:
                warnings.append(f"{section['label']}：{section['note']}")
        if cross_check and cross_check.get("conflict"):
            warnings.append(str(cross_check.get("note")))
        return warnings
