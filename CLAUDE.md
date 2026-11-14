# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

StockVal is a local-first stock research and valuation workbench for individual investors (UI and API messages are in Chinese). Enter a ticker (US/HK/A-share, anything Yahoo Finance covers), get a quote, a price chart, annual financials, and intrinsic-value estimates from two-stage DCF, WACC, scenarios, reverse DCF, multiples, Graham number, and Gordon DDM. Not investment advice.

## Architecture

Two apps plus a shared contract:

```
backend/   FastAPI + SQLAlchemy + Alembic + SQLite   →  http://127.0.0.1:8000
frontend/  React 18 + TS + Vite + Tailwind + ECharts →  http://127.0.0.1:5173
```

Backend layering is strict and worth preserving:

- [backend/app/api/](backend/app/api/) — routers only. Parse/validate via Pydantic schemas, call one service, wrap the result in `ApiResponse`.
- [backend/app/services/](backend/app/services/) — business orchestration. Owns caching, degradation, and `meta` (data lineage) assembly.
- [backend/app/repositories/](backend/app/repositories/) — SQLAlchemy data access.
- [backend/app/providers/](backend/app/providers/) — upstream adapters behind a `MarketDataProvider` Protocol. All providers return the same unified Pydantic models from `providers/models.py`.
- [backend/app/valuation/](backend/app/valuation/) — **pure computation, zero I/O**. Every function returns `None` when inputs are missing or the math doesn't hold.

Frontend: `src/api/` (typed client + TanStack Query hooks), `src/features/` (one folder per page), `src/components/` (shared UI), `src/lib/` (formatting).

Detailed requirements live in `docs/PRD.md` and task status in `docs/process.md` — both are kept local only and are not committed to the repository. **Update process.md whenever you complete a task** (status marker, phase counts, and change log).

## Commands

```bash
# Backend (requires Python 3.13+; use uv or venv)
cd backend
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/python -m pytest tests -q          # tests
.venv/bin/ruff check app tests               # lint
.venv/bin/ruff check app tests --fix         # autofix
.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Frontend (requires Node 20+)
cd frontend
npm install
npm run dev         # dev server, proxies /api → :8000
npm run typecheck
npm run build

# Docker
docker compose up -d --build    # web on :8080, api internal
```

There is no lint config for the frontend beyond `tsc --noEmit`; keep new TS strict-clean (`noUnusedLocals` is on).

## Offline verification

`STOCKVAL_DEMO=1` makes every data endpoint return built-in sample data with no network access. This is the
fastest way to verify changes and the default state for tests (`tests/conftest.py` sets it). Tests use a temp
SQLite DB per test and `Base.metadata.create_all`, so they don't need Alembic — `STOCKVAL_RUN_MIGRATIONS=0`
(also set in conftest) keeps the app lifespan from spawning an `alembic upgrade` subprocess on every TestClient
startup, which otherwise dominates the suite's runtime.

To verify a UI change, run both servers and check the API directly:

```bash
curl -s http://127.0.0.1:8000/api/v1/ping
curl -s -c /tmp/ck -X POST http://127.0.0.1:8000/api/v1/auth/bootstrap \
  -H 'Content-Type: application/json' -d '{"email":"a@b.com","password":"password123"}'
curl -s -b /tmp/ck http://127.0.0.1:8000/api/v1/stocks/AAPL/valuation
```

## Invariants worth preserving

- **Never fabricate data.** Missing fields are `null` and render as `—`. No estimates, no zero-filling, no interpolation. The only sanctioned fallbacks are *computational* (e.g. FCF = operating cash flow + capex, P/S = market cap ÷ revenue) and must be labelled with their formula.
- **Percentages are percentage points everywhere.** `growth=10` means 10%; conversion to fractions happens inside `app/valuation/`. `wacc()` takes `tax_rate=21` for 21% — do not pass a fraction.
- **Data lineage is mandatory.** Every response carries `meta.source`, `meta.as_of`, `meta.cached`, `meta.stale`, `meta.missing_fields`. `stale=true` means the cache had expired and the upstream failed — the service returns the stale copy rather than inventing data.
- **Ticker normalization** (strip + uppercase) lives in [backend/app/core/tickers.py](backend/app/core/tickers.py); service entry points call it before touching a provider.
- **Charts come from ECharts (npm)** and must render offline; there is no CDN dependency.
- **API field names are contracts.** `frontend/src/api/types.ts` mirrors the backend Pydantic schemas; changing one means changing the other.

## Estimation conventions

`ValuationService.build()` defaults: stage-one growth 10% over 5 years, terminal growth 2.5%, dividend growth 3%. Discount rate defaults to CAPM `r_f(currency) + beta × 5%` (r_f: USD 4.0 / CNY 2.5 / HKD 3.5, beta missing → 1.0) and is overridable via the `discount` param; `base_fcf` can also be overridden and is flagged as 用户输入 in `sources`. Balance-sheet debt/cash come from the latest annual statement first, falling back to quote-level totals; if either is still missing both become 0 and `inputs.balance_note` warns the user. The sensitivity table is discount rate ±1/±2 points against terminal growth 1.5/2.5/3.5%. The summary averages DCF, DDM (dividend yield > 0), and Graham (needs positive EPS *and* book value), lists each method with its equal weight in `summary.methods`, and maps ±15% versus price to 低估/高估/合理.

Historical valuation percentiles (`/valuation/history`, [backend/app/valuation/history.py](backend/app/valuation/history.py)) map every trading day to the latest fiscal year whose `period_end` is on or before that day — never a later statement — and skip days whose denominator is missing. Fewer than 20 samples means no percentile at all rather than a weak one.

Weighted summaries (`/valuation/summary`, [backend/app/valuation/summary.py](backend/app/valuation/summary.py)) require the user's weights to add up to 100% (±0.05) and reject unavailable methods instead of silently renormalising — the shown weights must equal the applied ones.

Portfolio totals ([backend/app/analysis/portfolio.py](backend/app/analysis/portfolio.py), pure) are `quantity × price × fx_rate`, where `fx_rate` is base-currency-per-holding-currency from `MarketService.get_fx_rate()`. Missing FX is never estimated: those holdings are excluded from base-currency totals and reported by currency, and weights only cover convertible rows so they still sum to 100%. An empty portfolio sums to 0; a portfolio whose every row is unconvertible returns `null` totals with a warning. There is no industry field upstream, so distribution is by market only.

Compare ([backend/app/analysis/compare.py](backend/app/analysis/compare.py)) fixes each metric's direction (higher/lower) on the server and returns `best`/`worst`, so the table never re-derives "best" per page; missing values never win or lose, and ties or a single value yield no ranking. All compared tickers are valued with the same DCF assumptions, with the CAPM discount rate still per currency.

Screening ([backend/app/analysis/screener.py](backend/app/analysis/screener.py)) treats a missing value as failing any bounded condition — a stock with no P/E must not pass `P/E < 20` just because nothing contradicts it — and sorts nulls last in both directions. The pool is capped at 500 symbols with 4 fetch workers; a failed ticker is reported in `failures` instead of failing the request.

Preset index constituents ([backend/app/providers/index_members.py](backend/app/providers/index_members.py)) are a dated built-in snapshot seeded into `index_constituents` with `updated_at` set to the snapshot date, not "now" — the UI must show that date and source. `POST /screener/indexes/{key}/refresh` replaces the list only when a provider actually supports `get_index_members()`; otherwise it keeps the existing list and returns `refreshed=false` with the reason, never an invented list.

## Archived legacy demo

The original Flask app is frozen at [archive/legacy-flask-demo/](archive/legacy-flask-demo/) and is no longer wired into anything. Don't extend it; the live app is `backend/` + `frontend/`.
