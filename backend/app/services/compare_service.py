"""多股对比服务：并发取数、统一假设估值与指标表（§5.10 FR-CMP-01 ~ 04）。

估值统一使用 `ValuationService.build()` 的默认假设（阶段一增速 10%、5 年、永续 2.5%），
折现率按各标的币种的 CAPM 默认值；返回体里注明这一点（FR-CMP-04）。
单只标的失败只影响该列，不中断整张表。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from app.analysis.compare import METRICS, best_worst, normalize_series
from app.core.errors import AppError, ErrorCode
from app.core.tickers import normalize_ticker
from app.services.market_service import MarketService
from app.services.quote_metrics import fetch_metrics

MIN_TICKERS = 2
MAX_TICKERS = 6
COMPARE_WORKERS = 6
UNIFIED_ASSUMPTIONS = {
    "growth": 10.0,
    "years1": 5,
    "terminal": 2.5,
    "note": "统一使用阶段一增速 10%/5 年、永续增速 2.5%；折现率取各标的币种的 CAPM 默认值。",
}


class CompareService:
    def __init__(self, market: MarketService | None = None) -> None:
        self.market = market or MarketService()

    def compare(self, tickers: list[str], period: str = "1y") -> dict[str, Any]:
        symbols: list[str] = []
        for raw in tickers:
            symbol = normalize_ticker(raw)
            if symbol and symbol not in symbols:
                symbols.append(symbol)
        if len(symbols) < MIN_TICKERS:
            raise AppError(
                ErrorCode.UNPROCESSABLE, f"请至少选择 {MIN_TICKERS} 只不同的标的", 422
            )
        if len(symbols) > MAX_TICKERS:
            raise AppError(
                ErrorCode.UNPROCESSABLE, f"最多对比 {MAX_TICKERS} 只标的", 422
            )

        with ThreadPoolExecutor(max_workers=min(len(symbols), COMPARE_WORKERS)) as pool:
            columns = list(pool.map(lambda s: self._column(s, period), symbols))

        metric_rows: list[dict[str, Any]] = []
        missing_by_ticker: dict[str, list[str]] = {}
        for spec in METRICS:
            values = {col["ticker"]: col["metrics"].get(spec.key) for col in columns}
            best, worst = best_worst(values, spec.direction)
            missing = [ticker for ticker, value in values.items() if value is None]
            for ticker in missing:
                missing_by_ticker.setdefault(ticker, []).append(spec.label)
            metric_rows.append(
                {
                    "key": spec.key,
                    "label": spec.label,
                    "unit": spec.unit,
                    "direction": spec.direction,
                    "values": values,
                    "best": best,
                    "worst": worst,
                    "missing": missing,
                }
            )

        warnings = [
            f"{col['ticker']}：{col['error']}" for col in columns if col["error"]
        ]
        if missing_by_ticker:
            detail = "；".join(
                f"{ticker} 缺 {'、'.join(labels)}"
                for ticker, labels in missing_by_ticker.items()
            )
            warnings.append(
                "部分指标缺失（显示为「—」，不参与优/差评选）：" + detail
            )
        currencies = {col["currency"] for col in columns if col["currency"]}
        if len(currencies) > 1:
            warnings.append(
                f"参与对比的标的计价货币不同（{'/'.join(sorted(currencies))}），"
                "金额类指标只能看数量级，不做汇率换算。"
            )

        return {
            "as_of": datetime.now(UTC),
            "period": period,
            "tickers": [
                {
                    "ticker": col["ticker"],
                    "name": col["name"],
                    "market": col["market"],
                    "currency": col["currency"],
                    "error": col["error"],
                }
                for col in columns
            ],
            "series": {col["ticker"]: col["series"] for col in columns},
            "metrics": metric_rows,
            "valuation": {
                "assumptions": UNIFIED_ASSUMPTIONS,
                "rows": [
                    {
                        "ticker": col["ticker"],
                        "per_share": col["valuation"]["per_share"],
                        "upside_pct": col["valuation"]["upside_pct"],
                        "price": col["valuation"]["price"],
                    }
                    for col in columns
                ],
            },
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    def _column(self, symbol: str, period: str) -> dict[str, Any]:
        column: dict[str, Any] = {
            "ticker": symbol,
            "name": symbol,
            "market": "UNKNOWN",
            "currency": None,
            "error": None,
            "metrics": {spec.key: None for spec in METRICS},
            "series": [],
            "valuation": {"per_share": None, "upside_pct": None, "price": None},
        }
        try:
            metrics = fetch_metrics(self.market, symbol)
        except AppError as exc:
            return {**column, "error": exc.message}

        column.update(
            name=metrics["name"],
            market=metrics["market"],
            currency=metrics["currency"],
            metrics={key: metrics.get(key) for key in column["metrics"]},
            valuation={
                "per_share": metrics["dcf_per_share"],
                "upside_pct": metrics["dcf_upside_pct"],
                "price": metrics["price"],
            },
        )

        try:
            bars, _hmeta = self.market.get_history(symbol, period=period, interval="1d")
        except AppError as exc:
            return {**column, "error": column["error"] or exc.message}
        points = [
            (bar.date.isoformat(), bar.close)
            for bar in bars
            if bar.close is not None
        ]
        column["series"] = normalize_series(points)
        return column
