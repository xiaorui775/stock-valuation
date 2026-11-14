"""估值预设对比（PRD §5.17 FR-RESEARCH-02）。

同一个标的、同一份行情与财务报表，只改变预设假设，输出各预设的 DCF 结果，
用于判断结论差异来自哪些输入。缺少 FCF 或股数时结果留空，不做估算。
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session as OrmSession

from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.services.market_service import MarketService
from app.services.preset_service import PresetService
from app.services.valuation_service import ValuationService

MIN_PRESETS = 2
MAX_PRESETS = 6


class PresetCompareService:
    def __init__(
        self, db: OrmSession, market: MarketService | None = None
    ) -> None:
        self.db = db
        self.presets = PresetService(db)
        self.market = market if market is not None else MarketService()

    def compare(
        self,
        user_id: int,
        ticker: str,
        preset_ids: Optional[list[int]] = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        ticker = normalize_ticker(ticker)
        available = {item["id"]: item for item in self.presets.list(user_id, ticker)}

        if preset_ids:
            # 保持用户选择顺序，同时去重
            ordered_ids = list(dict.fromkeys(preset_ids))
            missing = [pid for pid in ordered_ids if pid not in available]
            if missing:
                raise AppError(
                    ErrorCode.NOT_FOUND,
                    f"预设不存在：{', '.join(str(pid) for pid in missing)}",
                    404,
                )
            selected = [available[pid] for pid in ordered_ids]
        else:
            selected = list(available.values())

        if len(selected) < MIN_PRESETS:
            raise AppError(
                ErrorCode.UNPROCESSABLE,
                f"至少需要 {MIN_PRESETS} 个预设才能对比",
                422,
            )
        if len(selected) > MAX_PRESETS:
            raise AppError(
                ErrorCode.UNPROCESSABLE,
                f"一次最多对比 {MAX_PRESETS} 个预设",
                422,
            )

        quote, quote_meta = self.market.get_quote(ticker)
        try:
            financials, _ = self.market.get_financials(ticker)
        except AppError:
            financials = None

        rows = [
            self._row(preset, quote, financials) for preset in selected
        ]
        notes = ["所有预设使用同一份行情与财务报表，结果差异只来自假设。"]
        if any(row["per_share"] is None for row in rows):
            notes.append(
                "部分预设缺少可计算 DCF 的 FCF、股数或现价，结果留空，未做估算。"
            )

        data = {
            "ticker": ticker,
            "price": quote.price,
            "currency": quote.currency,
            "items": rows,
            "notes": notes,
        }
        return data, quote_meta

    @staticmethod
    def _row(preset: dict[str, Any], quote: Any, financials: Any) -> dict[str, Any]:
        assumptions = preset["assumptions"]
        valuation = ValuationService(quote, financials).build(
            growth=assumptions.get("growth"),
            terminal=assumptions.get("terminal"),
            discount=assumptions.get("discount"),
            ddm_growth=assumptions.get("ddm_growth"),
            years1=assumptions.get("years1"),
            base_fcf=assumptions.get("base_fcf"),
        )
        inputs = valuation.get("inputs") or {}
        dcf = valuation.get("dcf") or {}
        return {
            "preset_id": preset["id"],
            "name": preset["name"],
            "growth": inputs.get("growth"),
            "years1": inputs.get("years1"),
            "terminal": inputs.get("terminal"),
            "discount": inputs.get("discount"),
            "ddm_growth": inputs.get("ddm_growth"),
            "base_fcf": inputs.get("base_fcf"),
            "per_share": dcf.get("per_share"),
            "upside_pct": dcf.get("upside_pct"),
            "pv_terminal_ratio": dcf.get("pv_terminal_ratio"),
            "note": None if dcf else "缺少 FCF、股数或现价，DCF 无法计算",
        }
