"""估值服务：编排各模型，输出带假设与来源的完整结果。"""
from __future__ import annotations

from typing import Any, Optional

from app.providers.models import Financials, Quote
from app.valuation.dcf import dcf_value
from app.valuation.ddm import ddm_value
from app.valuation.graham import graham_number
from app.valuation.multiples import fcf_yield, safe_div
from app.valuation.reverse_dcf import implied_growth
from app.valuation.scenarios import build_scenarios
from app.valuation.wacc import capm_discount_rate, default_risk_free, wacc

DEFAULT_GROWTH = 10.0
DEFAULT_TERMINAL = 2.5
DEFAULT_DDM_GROWTH = 3.0
DEFAULT_YEARS1 = 5


class ValuationService:
    def __init__(self, quote: Quote, financials: Optional[Financials]) -> None:
        self.quote = quote
        self.financials = financials

    # ------------------------------------------------------------------
    def _latest(self) -> Any:
        years = self.financials.years if self.financials else []
        return years[0] if years else None

    def _balance(self) -> tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
        """返回 (总债务, 总现金, 股东权益, 缺失提示)。"""
        latest = self._latest()
        total_debt = getattr(latest, "total_debt", None) if latest else None
        if total_debt is None:
            total_debt = self.quote.total_debt
        total_cash = getattr(latest, "total_cash", None) if latest else None
        if total_cash is None:
            total_cash = self.quote.total_cash
        total_equity = getattr(latest, "total_equity", None) if latest else None
        note = None
        if total_debt is None or total_cash is None:
            note = "资产负债表债务/现金数据不完整，缺失项按 0 处理，DCF 结果可能偏高或偏低"
            total_debt = total_debt or 0
            total_cash = total_cash or 0
        return total_debt, total_cash, total_equity, note

    # ------------------------------------------------------------------
    def build(
        self,
        growth: Optional[float] = None,
        terminal: Optional[float] = None,
        discount: Optional[float] = None,
        ddm_growth: Optional[float] = None,
        years1: Optional[int] = None,
    ) -> dict[str, Any]:
        price = self.quote.price
        latest = self._latest()
        base_fcf = getattr(latest, "free_cash_flow", None)
        total_debt, total_cash, total_equity, balance_note = self._balance()
        shares = self.quote.shares_outstanding or getattr(latest, "shares_outstanding", None)

        beta = self.quote.beta
        default_discount = capm_discount_rate(beta)
        discount_rate = float(discount) if discount is not None else default_discount
        growth1 = float(growth) if growth is not None else DEFAULT_GROWTH
        terminal_g = float(terminal) if terminal is not None else DEFAULT_TERMINAL
        ddm_g = float(ddm_growth) if ddm_growth is not None else DEFAULT_DDM_GROWTH
        years = int(years1) if years1 is not None else DEFAULT_YEARS1

        # ---- DCF ----
        dcf = dcf_value(
            base_fcf, growth1, years, terminal_g, discount_rate,
            total_debt, total_cash, shares,
        )
        dcf_block = None
        if dcf:
            dcf_block = {
                "per_share": dcf["per_share"],
                "upside_pct": ((dcf["per_share"] - price) / price * 100) if price else None,
                "enterprise_value": dcf["enterprise_value"],
                "equity_value": dcf["equity_value"],
                "base_fcf": base_fcf,
                "pv_terminal_ratio": dcf["pv_terminal_ratio"],
                "formula": "EV = Σ FCF_t/(1+r)^t + TV/(1+r)^n；每股 = (EV − 债务 + 现金) / 股数",
            }

        # ---- 敏感性表 ----
        sensitivity = None
        if base_fcf is not None and shares:
            rows = []
            for offset in (-2, -1, 0, 1, 2):
                r_pct = discount_rate + offset
                cells = []
                for tg in (1.5, 2.5, 3.5):
                    res = dcf_value(
                        base_fcf, growth1, years, tg, r_pct,
                        total_debt, total_cash, shares,
                    )
                    cells.append(res["per_share"] if res else None)
                rows.append({"discount": r_pct, "values": cells})
            sensitivity = {"terminal_growths": [1.5, 2.5, 3.5], "rows": rows}

        # ---- 倍数 ----
        eps = self.quote.eps_ttm
        bvps = self.quote.book_value_per_share
        if bvps is None and total_equity and shares:
            bvps = total_equity / shares
        revenue = getattr(latest, "revenue", None) or self.quote.total_revenue
        market_cap = self.quote.market_cap or (price * shares if price and shares else None)
        ev = None
        if market_cap is not None:
            ev = market_cap + (total_debt or 0) - (total_cash or 0)
        multiples = [
            {"name": "P/E（市盈率）", "value": safe_div(price, eps),
             "formula": "股价 ÷ EPS(TTM)"},
            {"name": "P/S（市销率）",
             "value": self.quote.price_to_sales or safe_div(market_cap, revenue),
             "formula": "市值 ÷ 营业收入(TTM)"},
            {"name": "P/B（市净率）",
             "value": self.quote.price_to_book or safe_div(price, bvps),
             "formula": "股价 ÷ 每股净资产"},
            {"name": "EV/EBITDA",
             "value": self.quote.ev_ebitda or safe_div(ev, self.quote.ebitda),
             "formula": "企业价值 ÷ EBITDA"},
            {"name": "FCF Yield", "value": fcf_yield(base_fcf, market_cap),
             "formula": "自由现金流 ÷ 市值"},
        ]
        peg = self.quote.peg
        if peg is not None:
            multiples.append({"name": "PEG", "value": peg, "formula": "P/E ÷ 盈利增长率(%)"})
        graham = graham_number(eps, bvps)
        if graham is not None:
            multiples.append(
                {"name": "Graham 数字", "value": graham, "formula": "√(22.5 × EPS × 每股净资产)"}
            )

        # ---- 股利折现 ----
        ddm = None
        dy = self.quote.dividend_yield
        if dy and dy > 0:
            val = ddm_value(price, dy, ddm_g, discount_rate)
            if val is not None:
                ddm = {
                    "per_share": val,
                    "dividend_yield": dy,
                    "growth": ddm_g,
                    "discount": discount_rate,
                    "formula": "价值 = 每股股利 ×(1+g) ÷ (r − g)",
                }

        # ---- 综合 ----
        estimates = []
        if dcf_block:
            estimates.append(dcf_block["per_share"])
        if ddm:
            estimates.append(ddm["per_share"])
        if graham is not None:
            estimates.append(graham)
        summary = None
        if estimates and price:
            avg = sum(estimates) / len(estimates)
            diff = (avg - price) / price
            if diff > 0.15:
                band = "低估"
            elif diff < -0.15:
                band = "高估"
            else:
                band = "合理"
            summary = {
                "average_value": avg,
                "methods_used": len(estimates),
                "vs_price_pct": diff * 100,
                "band": band,
                "note": "判定规则：平均值高于现价 15% 以上为「低估」，低于 15% 以上为「高估」，其间为「合理」。这是模型输出，不是投资建议。",
            }

        return {
            "ticker": self.quote.ticker,
            "currency": self.quote.currency,
            "price": price,
            "inputs": {
                "base_fcf": base_fcf,
                "base_fcf_year": getattr(latest, "year", None),
                "growth": growth1,
                "years1": years,
                "terminal": terminal_g,
                "discount": discount_rate,
                "discount_default_capm": default_discount,
                "beta": beta,
                "total_debt": total_debt,
                "total_cash": total_cash,
                "shares_outstanding": shares,
                "balance_note": balance_note,
                "ddm_growth": ddm_g,
            },
            "dcf": dcf_block,
            "sensitivity": sensitivity,
            "multiples": multiples,
            "ddm": ddm,
            "graham": graham,
            "summary": summary,
            "disclaimer": "本工具仅供学习研究，不构成投资建议，估值结果取决于假设输入。",
        }

    # ------------------------------------------------------------------
    def scenarios(self, scenarios: list[dict], price: Optional[float] = None) -> dict[str, Any]:
        latest = self._latest()
        base_fcf = getattr(latest, "free_cash_flow", None)
        total_debt, total_cash, _, _ = self._balance()
        shares = self.quote.shares_outstanding or getattr(latest, "shares_outstanding", None)
        return build_scenarios(
            base_fcf, scenarios, total_debt, total_cash, shares,
            price if price is not None else self.quote.price,
        )

    # ------------------------------------------------------------------
    def reverse(
        self,
        price: Optional[float] = None,
        terminal: Optional[float] = None,
        discount: Optional[float] = None,
        years1: Optional[int] = None,
    ) -> dict[str, Any]:
        latest = self._latest()
        base_fcf = getattr(latest, "free_cash_flow", None)
        total_debt, total_cash, _, _ = self._balance()
        shares = self.quote.shares_outstanding or getattr(latest, "shares_outstanding", None)
        beta = self.quote.beta
        discount_rate = float(discount) if discount is not None else capm_discount_rate(beta)
        result = implied_growth(
            price if price is not None else self.quote.price,
            base_fcf,
            int(years1) if years1 is not None else DEFAULT_YEARS1,
            float(terminal) if terminal is not None else DEFAULT_TERMINAL,
            discount_rate,
            total_debt,
            total_cash,
            shares,
        )
        if result is None:
            return {"implied_growth": None, "reason": "缺少必要数据，无法求解"}
        return result

    # ------------------------------------------------------------------
    def wacc_params(
        self,
        risk_free: Optional[float] = None,
        beta: Optional[float] = None,
        erp: float = 5.0,
        cost_of_debt: float = 4.0,
        tax_rate: float = 21.0,
    ) -> dict[str, Any]:
        latest = self._latest()
        total_debt, _total_cash, _total_equity, _ = self._balance()
        shares = self.quote.shares_outstanding or getattr(latest, "shares_outstanding", None)
        market_cap = self.quote.market_cap or (
            self.quote.price * shares if self.quote.price and shares else None
        )
        rf = float(risk_free) if risk_free is not None else default_risk_free(self.quote.currency)
        b = beta if beta is not None else self.quote.beta
        result = wacc(rf, b, erp, cost_of_debt, tax_rate, total_debt, market_cap)
        return {
            "inputs": {
                "risk_free": rf,
                "beta": b,
                "erp": erp,
                "cost_of_debt": cost_of_debt,
                "tax_rate": tax_rate,
                "debt": total_debt,
                "equity": market_cap,
            },
            "result": result,
            "formula": "WACC = E/(D+E) × r_e + D/(D+E) × r_d × (1 − t)；r_e = r_f + β × ERP",
        }
