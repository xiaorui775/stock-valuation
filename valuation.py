"""估值模型：两阶段 DCF、估值倍数、Graham 公式、股利折现（Gordon 模型）。

所有函数只做模型计算并标注所用公式；缺失输入时对应方法返回 None，
绝不用编造数据填充。结果仅为模型输出，不构成投资建议。
"""


def _safe_div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def capm_discount_rate(beta, risk_free=4.0, erp=5.0):
    """CAPM：折现率(%) = 无风险利率 + Beta × 股权风险溢价。Beta 缺失时取 1.0。"""
    b = beta if beta is not None else 1.0
    return risk_free + b * erp


def dcf_value(base_fcf, growth1_pct, years1, terminal_growth_pct, discount_pct,
              total_debt, total_cash, shares):
    """两阶段 DCF，返回每股内在价值与中间量；输入不全或数学不成立时返回 None。

    阶段一：未来 years1 年 FCF 按 growth1 增长；
    终值：TV = FCF_n × (1+gT) / (r − gT)；
    企业价值 = Σ FCF_t/(1+r)^t + TV/(1+r)^n；
    股权价值 = 企业价值 − 总债务 + 现金；每股价值 = 股权价值 / 总股数。
    """
    if base_fcf is None or shares in (None, 0):
        return None
    r = discount_pct / 100.0
    g1 = growth1_pct / 100.0
    gt = terminal_growth_pct / 100.0
    if r <= gt or r <= -1:
        return None
    pv = 0.0
    fcf = base_fcf
    for t in range(1, years1 + 1):
        fcf = base_fcf * (1 + g1) ** t
        pv += fcf / (1 + r) ** t
    terminal = fcf * (1 + gt) / (r - gt)
    pv_terminal = terminal / (1 + r) ** years1
    ev = pv + pv_terminal
    equity = ev - (total_debt or 0) + (total_cash or 0)
    per_share = equity / shares
    return {
        "per_share": per_share,
        "enterprise_value": ev,
        "equity_value": equity,
        "pv_terminal_ratio": (pv_terminal / ev) if ev else None,
    }


def ddm_value(price, dividend_yield_pct, growth_pct, discount_pct):
    """Gordon 股利增长模型：价值 = DPS×(1+g) / (r − g)，DPS = 股价 × 股息率。"""
    if not dividend_yield_pct or dividend_yield_pct <= 0 or price is None:
        return None
    r, g = discount_pct / 100.0, growth_pct / 100.0
    if r <= g:
        return None
    dps = price * dividend_yield_pct / 100.0
    return dps * (1 + g) / (r - g)


def graham_number(eps, book_value_per_share):
    """Graham 数字 = √(22.5 × EPS × 每股净资产)。"""
    if eps is None or book_value_per_share is None or eps <= 0 or book_value_per_share <= 0:
        return None
    return (22.5 * eps * book_value_per_share) ** 0.5


def build_valuation(quote, financials, params):
    """组装 /api/valuation 的完整结果。

    params 可覆盖：growth（阶段一增速%）、terminal（永续增速%）、
    discount（折现率%，不传则用 CAPM 预填）、ddm_growth（股利增速%）。
    """
    price = quote.get("price")
    years = (financials or {}).get("years") or []
    latest = years[0] if years else {}
    base_fcf = latest.get("free_cash_flow")

    # 资产负债表优先取最新报表，取不到再用 quote 里的汇总值
    balance = (financials or {}).get("balance_latest") or {}
    total_debt = balance.get("total_debt")
    if total_debt is None:
        total_debt = quote.get("total_debt")
    total_cash = balance.get("total_cash")
    if total_cash is None:
        total_cash = quote.get("total_cash")
    balance_note = None
    if total_debt is None or total_cash is None:
        balance_note = "资产负债表债务/现金数据不完整，缺失项按 0 处理，DCF 结果可能偏高或偏低"
        total_debt = total_debt or 0
        total_cash = total_cash or 0

    beta = quote.get("beta")
    default_discount = capm_discount_rate(beta)
    discount = params.get("discount")
    discount = float(discount) if discount is not None else default_discount
    growth1 = float(params.get("growth", 10.0))
    terminal = float(params.get("terminal", 2.5))
    ddm_growth = float(params.get("ddm_growth", 3.0))
    shares = quote.get("shares_outstanding")

    dcf = dcf_value(base_fcf, growth1, 5, terminal, discount,
                    total_debt, total_cash, shares)
    dcf_block = None
    if dcf:
        dcf_block = {
            "per_share": dcf["per_share"],
            "upside_pct": ((dcf["per_share"] - price) / price * 100) if price else None,
            "enterprise_value": dcf["enterprise_value"],
            "equity_value": dcf["equity_value"],
            "base_fcf": base_fcf,
            "pv_terminal_ratio": dcf["pv_terminal_ratio"],
        }

    # 敏感性表：行 = 折现率 ±2/±1/0 个百分点，列 = 永续增速 1.5/2.5/3.5%
    sensitivity = None
    if base_fcf is not None and shares:
        rows = []
        for offset in (-2, -1, 0, 1, 2):
            r_pct = discount + offset
            cells = []
            for tg in (1.5, 2.5, 3.5):
                res = dcf_value(base_fcf, growth1, 5, tg, r_pct,
                                total_debt, total_cash, shares)
                cells.append(res["per_share"] if res else None)
            rows.append({"discount": r_pct, "values": cells})
        sensitivity = {"terminal_growths": [1.5, 2.5, 3.5], "rows": rows}

    # ---- 估值倍数（值 + 公式）----
    eps = quote.get("eps_ttm")
    bvps = quote.get("book_value_per_share")
    if bvps is None and balance.get("total_equity") and shares:
        bvps = balance["total_equity"] / shares
    revenue = latest.get("revenue") or quote.get("total_revenue")
    market_cap = quote.get("market_cap") or (price * shares if price and shares else None)
    ev = None
    if market_cap is not None:
        ev = market_cap + (total_debt or 0) - (total_cash or 0)
    multiples = [
        {"name": "P/E（市盈率）", "value": _safe_div(price, eps),
         "formula": "股价 ÷ EPS(TTM)"},
        {"name": "P/S（市销率）", "value": quote.get("price_to_sales") or _safe_div(market_cap, revenue),
         "formula": "市值 ÷ 营业收入(TTM)"},
        {"name": "P/B（市净率）", "value": quote.get("price_to_book") or _safe_div(price, bvps),
         "formula": "股价 ÷ 每股净资产"},
        {"name": "EV/EBITDA", "value": quote.get("ev_ebitda") or _safe_div(ev, quote.get("ebitda")),
         "formula": "企业价值 ÷ EBITDA"},
    ]
    peg = quote.get("peg")  # 仅使用数据源给出的 PEG，无则省略
    if peg is not None:
        multiples.append({"name": "PEG", "value": peg,
                          "formula": "P/E ÷ 盈利增长率(%)"})
    graham = graham_number(eps, bvps)
    if graham is not None:
        multiples.append({"name": "Graham 数字", "value": graham,
                          "formula": "√(22.5 × EPS × 每股净资产)"})

    # ---- 股利折现 ----
    ddm = None
    dy = quote.get("dividend_yield")
    if dy and dy > 0:
        val = ddm_value(price, dy, ddm_growth, discount)
        if val is not None:
            ddm = {"per_share": val, "dividend_yield": dy,
                   "growth": ddm_growth, "discount": discount}

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
        summary = {"average_value": avg, "methods_used": len(estimates),
                   "vs_price_pct": diff * 100, "band": band}

    return {
        "ticker": quote.get("ticker"),
        "currency": quote.get("currency"),
        "demo": quote.get("demo", False),
        "price": price,
        "inputs": {
            "base_fcf": base_fcf,
            "growth": growth1,
            "terminal": terminal,
            "discount": discount,
            "discount_default_capm": default_discount,
            "beta": beta,
            "total_debt": total_debt,
            "total_cash": total_cash,
            "shares_outstanding": shares,
            "balance_note": balance_note,
            "ddm_growth": ddm_growth,
        },
        "dcf": dcf_block,
        "sensitivity": sensitivity,
        "multiples": multiples,
        "ddm": ddm,
        "graham": graham,
        "summary": summary,
        "disclaimer": "本工具仅供学习研究，不构成投资建议，估值结果取决于假设输入。",
    }
