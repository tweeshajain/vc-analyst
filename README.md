# ai-vc-analyst

Full-stack local app: **FastAPI** (Python) + **SQLite** + **React** (Vite) dashboard for startup radar, investment memos, and deal tracking.

## Layout

- `backend/` — FastAPI app (`backend/app/`), requirements, SQLAlchemy models
- `frontend/` — Vite + React UI (proxies `/api` to the backend)
- `modules/radar`, `modules/memo`, `modules/deals`, `modules/pipeline` — feature routers and orchestration

SQLite file: `data/app.db` (created on first run).

## Prerequisites

- Python 3.11+ recommended
- Node.js 18+ and npm

## Backend setup

From the **project root** (`ai-vc-analyst/`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Start the API (must run from project root so `backend` and `modules` import correctly):

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- OpenAPI docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/api/health  

### API routes

| Prefix | Description |
|--------|-------------|
| `/api/radar` | Startups and scores (radar) |
| `/api/radar/top-startups` | Top 10 startups by engagement `radar_score` |
| `/api/memo` | Investment memos (incl. generator) |
| `/api/deals` | Deals (tracked opportunities) |
| `/api/deals/top` | Top 5 investment-worthy startups (composite deal score) |
| `/api/pipeline/run` | Run full daily pipeline (Radar → score → memos → deal snapshot) |
| `/api/pipeline/history/runs` | Recent pipeline runs (IDs, status, summary metrics) |
| `/api/pipeline/history/top-startups` | Append-only history of top-startup leaderboards per completed run |

### Orchestrated pipeline (`GET /api/pipeline/run`)

Runs **`run_daily_pipeline()`**, which:

1. **Radar** — Fetches trending rows (Product Hunt + Reddit) and **upserts** into `startups` (dedupe on `source` + `external_id`).
2. **Score** — Recomputes **`radar_score`** from engagement for **all** startups (including manual rows).
3. **Memos** — Generates **structured memos** for high-traction startups first (by `radar_score`), up to **`PIPELINE_MEMO_LIMIT`** (default 40) **new** memos per run; skips startups that already have a **`generated`** memo within **`PIPELINE_MEMO_COOLDOWN_HOURS`** (default 24).
4. **Deals** — Builds the **top 5 deal snapshot** (same logic as Deal Finder) and stores it under **`top_deals`** in the run record.
5. **Radar leaderboard** — Computes the **top 10** startups (same logic as `GET /api/radar/top-startups`), stores **`top_startups`** in **`stats_json`**, and appends a row to **`top_startups_snapshots`** for history.

**Persistence:** Each execution writes a **`pipeline_runs`** row (`status`, `stats_json` with metrics + `top_deals` + `top_startups`, optional `error_message`). Successful runs also write **`top_startups_snapshots`** (JSON leaderboard tied to `pipeline_run_id`).

**Duplicate avoidance:** Default **60-minute** cooldown between successful runs (`PIPELINE_COOLDOWN_MINUTES`). Skip if another run is **`running`** (runs older than `PIPELINE_STALE_LOCK_MINUTES` are marked failed first). Use **`GET /api/pipeline/run?force=true`** to bypass cooldown/guards (still clears stale locks).

Environment overrides: `PIPELINE_COOLDOWN_MINUTES`, `PIPELINE_MEMO_LIMIT`, `PIPELINE_MEMO_COOLDOWN_HOURS`, `PIPELINE_STALE_LOCK_MINUTES`.

### Automation (scheduler, logs, no manual steps)

- **Daily scheduler:** When the API process starts, **APScheduler** schedules the same pipeline **once per day** at **`PIPELINE_SCHEDULE_HOUR_UTC`:`PIPELINE_SCHEDULE_MINUTE`** (defaults **6** and **0** → **06:00 UTC**). Set **`PIPELINE_SCHEDULER_ENABLED=false`** to turn it off. Scheduled runs use **no cooldown** against the last API run so the daily job is not skipped; overlap with an in-flight run is still avoided via the in-progress guard.
- **Logging:** On startup, **`setup_logging()`** writes rotated logs to **`data/logs/app.log`** (and echoes INFO+ to stderr). Pipeline steps, API **`/api/pipeline/run`**, scheduler jobs, and **`log.exception`** traces on failures are recorded there.
- **Hands-off operation:** Keep **`uvicorn`** (or your process manager) running continuously; the scheduler and logging require no interactive input.

### Deal Finder (`GET /api/deals/top`)

**deal_score** (0–100) combines normalized **engagement** (stored `radar_score`), **keyword signals** (AI, automation, growth, revenue, etc.), and **novelty** (fewer textually similar peers in the DB ⇒ less “repeated idea” crowding). The response **stage** field is still **`early` vs `growth`** (investment readiness); optional **filters** narrow **who enters the ranking**:

| Query | Values | Meaning |
|-------|--------|---------|
| `industry` | `AI`, `SaaS`, `health` | Keyword match on name / sector / description |
| `stage` | `pre-seed`, `seed` | Match against text in each startup’s **`Startup.stage`** field (e.g. “Seed”, “Pre-seed”) |

Examples: `GET /api/deals/top?industry=AI&stage=seed`, `GET /api/deals/top?industry=SaaS`. Invalid filter values return **400**. Response rows include **name**, **score**, **stage** (`early`/`growth`), and **rationale**.

### Investment Memo Generator

- **`POST /api/memo/generate`** — body `{"startup_id": <int>}`. Runs `generate_memo(startup)` (template-based, offline “LLM-style” prose) and **inserts** a new row with `status: "generated"` and six sections in the DB.
- **`GET /api/memo/{startup_id}`** — returns the **latest** memo for that startup (by `created_at`).

Sections stored include **Company Overview**, **Market Opportunity**, **Business Model**, **Competitive Landscape** (3–5 keyword/database-derived comparables plus archetypes), **Differentiation Analysis**, **Strengths vs Competitors**, **Market Structure & Competition**, **Risks**, **Investment Thesis** (plus `summary` = executive one-liner, `title` = memo title). The React **Investment Memos** tab can generate memos from the dropdown.

### Startup Radar: fetch trending (Product Hunt + Reddit)

From the project root, with dependencies installed:

```powershell
python -m modules.radar.cli_fetch
```

- **Product Hunt:** set `PRODUCT_HUNT_TOKEN` for [Product Hunt API](https://api.producthunt.com/v2/docs) (GraphQL). If unset or the request fails, the job uses **mock** PH-style records.
- **Reddit:** reads public `hot.json` from `r/startups`, `r/SideProject`, and `r/EntrepreneurRideAlong`. Set `REDDIT_USER_AGENT` to a descriptive string (recommended by Reddit).
- **Scoring:** `radar_score = RADAR_WEIGHT_UPVOTES * upvotes + RADAR_WEIGHT_COMMENTS * comments` (defaults `1.0` and `2.0`).

Data is **upserted** into the `startups` table on `(source, external_id)`.

### Startup Radar ranking (`GET /api/radar/top-startups`)

The leaderboard adds **keyword boosts** on name + description for high-signal terms (e.g. AI, automation, growth, revenue), **dedupes** rows (same external domain or Product Hunt slug / normalized title), sorts by **composite raw score** (engagement + boosts), then applies **min–max normalization to 0–100** across the **top 10** slice.

Each item includes **`score`** (normalized), **`ranking_reason`** (short explanation), and **`radar_score`** (engagement-only value persisted in the DB).

## Frontend setup

In a **second** terminal, from `ai-vc-analyst/frontend`:

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173 — the dev server proxies `/api` to port 8000.

## End-to-end flow

1. Start the backend, then the frontend (order matters so the UI can reach the API).
2. **Startup Radar** — add startups and dimension scores (stored in `startups` and `scores` tables).
3. **Investment Memos** — create memos, optionally linked to a startup.
4. **Deal Finder** — log deals tied to a startup (add startups in Radar first if the list is empty).

On first launch with an empty database, a small demo **Acme AI** record (startup, score, memo, deal) is inserted so the dashboard is not blank.

## Production build (optional)

```powershell
cd frontend
npm run build
```

Static assets are emitted to `frontend/dist/`. Put a reverse proxy in front so `/api` routes to the FastAPI process.
