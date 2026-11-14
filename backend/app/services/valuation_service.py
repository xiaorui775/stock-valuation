"""估值服务：编排各模型，输出带假设与来源的完整结果。"""
from __future__ import annotations

from typing import Any, Optional

from app.providers.models import Financials, Quote
from app.valuation.dcf import dcf_three_stage, dcf_value
from app.valuation.ddm import ddm_three_stage, ddm_value
from app.valuation.graham import graham_number
from app.valuation.multiples import fcf_yield, safe_div
from app.valuation.reverse_dcf import implied_growth
from app.valuation.scenarios import build_scenarios
from app.valuation.summary import WEIGHT_TOLERANCE, combine
from app.valuation.wacc import capm_discount_rate, default_risk_free, wacc

DEFAULT_GROWTH = 10.0
DEFAULT_TERMINAL = 2.5
DEFAULT_DDM_GROWTH = 3.0
DEFAULT_YEARS1 = 5
DEFAULT_FADE_YEARS = 5


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

    def _balance_sources(self) -> dict[str, str]:
        """记录债务/现金/权益取自哪里（FR-VAL-06）。"""
        latest = self._latest()
        if getattr(latest, "total_debt", None) is not None:
            debt = "最新年报"
        elif self.quote.total_debt is not None:
            debt = "行情快照"
        else:
            debt = "缺失（按 0 处理）"
        if getattr(latest, "total_cash", None) is not None:
            cash = "最新年报"
        elif self.quote.total_cash is not None:
            cash = "行情快照"
        else:
            cash = "缺失（按 0 处理）"
        equity = (
            "最新年报"
            if getattr(latest, "total_equity", None) is not None
            else "缺失（改用行情每股净资产）"
        )
        return {"debt": debt, "cash": cash, "equity": equity}

    # ------------------------------------------------------------------
    def build(
        self,
        growth: Optional[float] = None,
        terminal: Optional[float] = None,
        discount: Optional[float] = None,
        ddm_growth: Optional[float] = None,
        years1: Optional[int] = None,
        base_fcf: Optional[float] = None,
    ) -> dict[str, Any]:
        price = self.quote.price
        latest = self._latest()
        reported_fcf = getattr(latest, "free_cash_flow", None)
        # 用户可覆盖基准 FCF（FR-VAL-01）；覆盖时保留来源标记
        fcf_override = base_fcf is not None
        effective_fcf = float(base_fcf) if fcf_override else reported_fcf
        total_debt, total_cash, total_equity, balance_note = self._balance()
        shares = self.quote.shares_outstanding or getattr(latest, "shares_outstanding", None)
        shares_source = (
            "行情快照"
            if self.quote.shares_outstanding
            else ("最新年报" if getattr(latest, "shares_outstanding", None) else "缺失")
        )

        beta = self.quote.beta
        # 无风险利率按币种预填（与 WACC 计算器口径一致）
        risk_free = default_risk_free(self.quote.currency)
        default_discount = capm_discount_rate(beta, risk_free)
        discount_rate = float(discount) if discount is not None else default_discount
        growth1 = float(growth) if growth is not None else DEFAULT_GROWTH
        terminal_g = float(terminal) if terminal is not None else DEFAULT_TERMINAL
        ddm_g = float(ddm_growth) if ddm_growth is not None else DEFAULT_DDM_GROWTH
        years = int(years1) if years1 is not None else DEFAULT_YEARS1

        # ---- DCF ----
        dcf = dcf_value(
            effective_fcf, growth1, years, terminal_g, discount_rate,
            total_debt, total_cash, shares,
        )
        dcf_block = None
        if dcf:
            dcf_block = {
                "per_share": dcf["per_share"],
                "upside_pct": ((dcf["per_share"] - price) / price * 100) if price else None,
                "enterprise_value": dcf["enterprise_value"],
                "equity_value": dcf["equity_value"],
                "base_fcf": effective_fcf,
                "pv_terminal_ratio": dcf["pv_terminal_ratio"],
                "formula": "EV = Σ FCF_t/(1+r)^t + TV/(1+r)^n；每股 = (EV − 债务 + 现金) / 股数",
            }

        # ---- 敏感性表 ----
        sensitivity = None
        if effective_fcf is not None and shares:
            rows = []
            for offset in (-2, -1, 0, 1, 2):
                r_pct = discount_rate + offset
                cells = []
                for tg in (1.5, 2.5, 3.5):
                    res = dcf_value(
                        effective_fcf, growth1, years, tg, r_pct,
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
            {"name": "Forward P/E（预期市盈率）", "value": self.quote.forward_pe,
             "formula": "股价 ÷ 预期 EPS"},
            {"name": "P/S（市销率）",
             "value": self.quote.price_to_sales or safe_div(market_cap, revenue),
             "formula": "市值 ÷ 营业收入(TTM)"},
            {"name": "P/B（市净率）",
             "value": self.quote.price_to_book or safe_div(price, bvps),
             "formula": "股价 ÷ 每股净资产"},
            {"name": "EV/EBITDA",
             "value": self.quote.ev_ebitda or safe_div(ev, self.quote.ebitda),
             "formula": "企业价值 ÷ EBITDA"},
            {"name": "FCF Yield", "value": fcf_yield(effective_fcf, market_cap),
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
        methods: list[dict[str, Any]] = []
        if dcf_block:
            methods.append({"name": "DCF", "value": dcf_block["per_share"]})
        if ddm:
            methods.append({"name": "DDM", "value": ddm["per_share"]})
        if graham is not None:
            methods.append({"name": "Graham", "value": graham})

        summary = None
        if methods and price:
            # 默认等权；用户自定义权重在 FR-VAL-13（M2-08）实现
            weight = 100.0 / len(methods)
            for item in methods:
                item["weight"] = weight
            avg = sum(item["value"] for item in methods) / len(methods)
            diff = (avg - price) / price
            if diff > 0.15:
                band = "低估"
            elif diff < -0.15:
                band = "高估"
            else:
                band = "合理"
            summary = {
                "average_value": avg,
                "methods_used": len(methods),
                "methods": methods,
                "vs_price_pct": diff * 100,
                "band": band,
                "note": "判定规则：平均值高于现价 15% 以上为「低估」，低于 15% 以上为「高估」，其间为「合理」。默认等权，这是模型输出，不是投资建议。",
            }

        return {
            "ticker": self.quote.ticker,
            "currency": self.quote.currency,
            "price": price,
            "inputs": {
                "base_fcf": effective_fcf,
                "base_fcf_year": getattr(latest, "year", None),
                "base_fcf_source": "用户输入" if fcf_override else "最新年报",
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
            "sources": {
                "fcf": {
                    "value": effective_fcf,
                    "year": getattr(latest, "year", None),
                    "origin": "用户输入" if fcf_override else "最新年报",
                    "field": "free_cash_flow",
                },
                "balance": {
                    "values": {
                        "debt": total_debt,
                        "cash": total_cash,
                        "equity": total_equity,
                    },
                    "origins": self._balance_sources(),
                    "note": balance_note,
                },
                "shares": {"value": shares, "origin": shares_source},
                "beta": {
                    "value": beta,
                    "origin": "行情快照" if beta is not None else "缺失（按 1.0 计算）",
                },
                "capm": {
                    "risk_free": risk_free,
                    "erp": 5.0,
                    "beta_used": beta if beta is not None else 1.0,
                    "value": default_discount,
                    "formula": f"r = r_f + β × ERP = {risk_free:g}% + β × 5%",
                },
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
    def multistage(
        self,
        growth: Optional[float] = None,
        terminal: Optional[float] = None,
        discount: Optional[float] = None,
        years1: Optional[int] = None,
        fade_years: Optional[int] = None,
        base_fcf: Optional[float] = None,
    ) -> dict[str, Any]:
        """三阶段 DCF / DDM：显式期 + 增速线性衰减期 + 永续期（FR-VAL-12）。"""
        price = self.quote.price
        latest = self._latest()
        reported_fcf = getattr(latest, "free_cash_flow", None)
        effective_fcf = float(base_fcf) if base_fcf is not None else reported_fcf
        total_debt, total_cash, _, balance_note = self._balance()
        shares = self.quote.shares_outstanding or getattr(latest, "shares_outstanding", None)

        risk_free = default_risk_free(self.quote.currency)
        default_discount = capm_discount_rate(self.quote.beta, risk_free)
        discount_rate = float(discount) if discount is not None else default_discount
        growth1 = float(growth) if growth is not None else DEFAULT_GROWTH
        terminal_g = float(terminal) if terminal is not None else DEFAULT_TERMINAL
        years = int(years1) if years1 is not None else DEFAULT_YEARS1
        fade = int(fade_years) if fade_years is not None else DEFAULT_FADE_YEARS

        dcf = dcf_three_stage(
            effective_fcf, growth1, years, fade, terminal_g, discount_rate,
            total_debt, total_cash, shares,
        )
        dcf_block = None
        if dcf is not None:
            per_share = dcf["per_share"]
            dcf_block = {
                "per_share": per_share,
                "upside_pct": ((per_share - price) / price * 100) if price else None,
                "enterprise_value": dcf["enterprise_value"],
                "equity_value": dcf["equity_value"],
                "base_fcf": effective_fcf,
                "pv_terminal_ratio": dcf["pv_terminal_ratio"],
                "years": dcf["years"],
            }

        dividend_yield = self.quote.dividend_yield
        ddm: Optional[dict[str, Any]] = None
        ddm_reason: Optional[str] = None
        if not dividend_yield or dividend_yield <= 0:
            ddm_reason = "该标的没有股息（股息率缺失或为 0），DDM 不适用"
        else:
            result = ddm_three_stage(
                price, dividend_yield, growth1, years, fade, terminal_g, discount_rate
            )
            if result is None:
                ddm_reason = "折现率不高于永续增速，股利折现模型不成立"
            else:
                ddm = {
                    "per_share": result["per_share"],
                    "upside_pct": (
                        (result["per_share"] - price) / price * 100 if price else None
                    ),
                    "dividend_yield": dividend_yield,
                    "dps": result["dps"],
                    "pv_explicit": result["pv_explicit"],
                    "pv_fade": result["pv_fade"],
                    "pv_terminal": result["pv_terminal"],
                    "terminal_ratio": result["terminal_ratio"],
                    "years": result["years"],
                }

        missing: list[str] = []
        if effective_fcf is None:
            missing.append("缺少自由现金流，无法计算 DCF")
        if not shares:
            missing.append("缺少总股本，无法换算每股价值")
        if balance_note:
            missing.append(balance_note)

        return {
            "ticker": self.quote.ticker,
            "currency": self.quote.currency,
            "price": price,
            "assumptions": {
                "growth": growth1,
                "years1": years,
                "fade_years": fade,
                "terminal": terminal_g,
                "discount": discount_rate,
                "discount_default_capm": default_discount,
                "base_fcf": effective_fcf,
                "base_fcf_source": "用户输入" if base_fcf is not None else "最新年报",
                "ddm_growth": growth1,
            },
            "dcf": dcf_block,
            "ddm": ddm,
            "ddm_reason": ddm_reason,
            "missing": missing,
            "formula": (
                "阶段一 growth×(years1 年) → 阶段二 增速线性衰减到永续增速(fade_years 年) → "
                "阶段三 TV = FCF_n×(1+g)/(r−g)，全部按 (1+r)^t 折现"
            ),
            "disclaimer": "本工具仅供学习研究，不构成投资建议，估值结果取决于假设输入。",
        }

    # ------------------------------------------------------------------
    def available_methods(self) -> dict[str, float]:
        """当前可用的估值方法与每股价值，口径与 `build()` 完全一致。"""
        data = self.build()
        values: dict[str, float] = {}
        if data["dcf"]:
            values["DCF"] = data["dcf"]["per_share"]
        if data["ddm"]:
            values["DDM"] = data["ddm"]["per_share"]
        if data["graham"] is not None:
            values["Graham"] = data["graham"]
        return values

    def weighted_summary(self, selection: list[dict]) -> dict[str, Any]:
        """按用户选择的方法与权重合成综合估值（FR-VAL-13）。

        权重合计必须为 100，不做静默归一化——否则界面显示的权重与实际生效的不一致。
        """
        values = self.available_methods()
        available = [{"name": name, "value": value} for name, value in values.items()]

        errors: list[str] = []
        entries: list[tuple[str, float, float]] = []
        for item in selection:
            name = str(item.get("name", ""))
            weight = float(item.get("weight", 0) or 0)
            if name not in values:
                errors.append(f"方法当前不可用：{name}")
                continue
            entries.append((name, values[name], weight))

        total = sum(weight for _, _, weight in entries)
        if not entries:
            errors.append("至少选择一个估值方法")
        elif abs(total - 100.0) > WEIGHT_TOLERANCE:
            errors.append(f"权重合计必须为 100%（当前 {total:g}%）")

        if errors:
            return {
                "available": available,
                "weighted_value": None,
                "vs_price_pct": None,
                "band": None,
                "methods": [],
                "total_weight": total,
                "error": "；".join(errors),
            }

        result = combine(entries, self.quote.price)
        if result is None:
            return {
                "available": available,
                "weighted_value": None,
                "vs_price_pct": None,
                "band": None,
                "methods": [],
                "total_weight": total,
                "error": "无法合成：权重或现价无效",
            }
        return {
            "available": available,
            "weighted_value": result["average_value"],
            "vs_price_pct": result["vs_price_pct"],
            "band": result["band"],
            "methods": result["methods"],
            "total_weight": result["total_weight"],
            "error": None,
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
