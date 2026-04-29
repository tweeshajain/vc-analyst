import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Project root (folder containing `backend/` and `modules/`) must be on sys.path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import Base, SessionLocal, engine
from backend.app.sqlite_migrate import (
    ensure_memo_structure_columns,
    ensure_pipeline_runs_table,
    ensure_startup_radar_columns,
    ensure_top_startups_snapshots_table,
)
from backend.app import models  # noqa: F401 — register ORM models with Base
from backend.app.models import Deal, InvestmentMemo, Score, Startup
from modules.deals.routes import router as deals_router
from modules.memo.routes import router as memo_router
from modules.pipeline.routes import router as pipeline_router
from modules.radar.routes import router as radar_router

Base.metadata.create_all(bind=engine)
ensure_startup_radar_columns(engine)
ensure_memo_structure_columns(engine)
ensure_pipeline_runs_table(engine)
ensure_top_startups_snapshots_table(engine)


def _seed_demo_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(Startup).count() > 0:
            return
        s = Startup(
            name="Acme AI",
            sector="Enterprise SaaS",
            stage="Series A",
            description="Demo company for local development.",
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        db.add(
            Score(
                startup_id=s.id,
                category="Team",
                value=78.0,
                notes="Strong founding team.",
            )
        )
        db.add(
            InvestmentMemo(
                title="Acme AI — initial screen",
                summary="Positive early signals; follow up on GTM.",
                status="draft",
                startup_id=s.id,
            )
        )
        db.add(
            Deal(
                startup_id=s.id,
                label="Acme Series A",
                round_name="Series A",
                status="diligence",
                notes="Introduced via partner meeting.",
            )
        )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.logging_setup import setup_logging

    setup_logging()

    from modules.pipeline.scheduler import shutdown_scheduler, start_scheduler

    start_scheduler()
    _seed_demo_if_empty()
    yield
    shutdown_scheduler()


app = FastAPI(title="ai-vc-analyst", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(radar_router, prefix="/api/radar", tags=["radar"])
app.include_router(memo_router, prefix="/api/memo", tags=["memo"])
app.include_router(deals_router, prefix="/api/deals", tags=["deals"])
app.include_router(pipeline_router, prefix="/api/pipeline", tags=["pipeline"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-vc-analyst"}
