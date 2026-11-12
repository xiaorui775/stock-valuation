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

Detailed requirements live in [docs/PRD.md](docs/PRD.md); task status in [docs/process.md](docs/process.md) — **update process.md whenever you complete a task** (status marker, phase counts, and change log).

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
SQLite DB per test and `Base.metadata.create_all`, so they don't need Alembic.

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
- **Ticker normalization** (strip + uppercase) happens at the top of each `data_service`/`market_service` entry point.
- **Chart.js is vendored** for the legacy Demo; the new frontend uses ECharts from npm. Either way, charts must render offline.
- **DOM IDs and API field names are contracts.** `templates/index.html` ↔ `static/app.js` for the legacy Demo; `src/api/types.ts` ↔ backend Pydantic schemas for the new app.

## Estimation conventions

`ValuationService.build()` defaults: stage-one growth 10% over 5 years, terminal growth 2.5%, dividend growth 3%. Discount rate defaults to CAPM `4% + beta × 5%` (beta missing → 1.0) and is overridable via the `discount` param. Balance-sheet debt/cash come from the latest annual statement first, falling back to quote-level totals; if either is still missing both become 0 and `inputs.balance_note` warns the user. The sensitivity table is discount rate ±1/±2 points against terminal growth 1.5/2.5/3.5%. The summary averages DCF, DDM (dividend yield > 0), and Graham (needs positive EPS *and* book value) and maps ±15% versus price to 低估/高估/合理.

## Legacy Demo

The original Flask app still lives at the repo root (`app.py`, `data_service.py`, `valuation.py`, `templates/`, `static/`).
It is superseded by `backend/` + `frontend/` and should be archived once M1 is done — don't extend it.
