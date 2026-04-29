import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import PipelineRun, TopStartupsSnapshot
from modules.pipeline.runner import run_daily_pipeline

router = APIRouter()
log = logging.getLogger("ai_vc_analyst.pipeline")


@router.get("/run")
def pipeline_run(
    force: bool = Query(
        False,
        description="Bypass cooldown and in-progress guard (still clears stale locks).",
    ),
    db: Session = Depends(get_db),
):
    """
    Execute the full pipeline: Radar import → rescore → memos → deal + radar snapshots.

    Results: `pipeline_runs.stats_json` and `top_startups_snapshots` history rows.
    """
    log.info("API /pipeline/run invoked force=%s", force)
    try:
        out = run_daily_pipeline(db, force=force, trigger="api")
        log.info("API pipeline finished status=%s", out.get("status"))
        return out
    except Exception as e:
        log.exception("API pipeline failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/history/runs")
def pipeline_history_runs(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Recent pipeline executions (newest first)."""
    rows = (
        db.query(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        payload: dict = {}
        try:
            payload = json.loads(r.stats_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        out.append(
            {
                "id": r.id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "status": r.status,
                "trigger": r.trigger,
                "error_message": r.error_message,
                "summary": {
                    "trending_rows_processed": payload.get("trending_rows_processed"),
                    "memos_created": payload.get("memos_created"),
                    "top_startups_count": len(payload.get("top_startups") or []),
                    "top_deals_count": len(payload.get("top_deals") or []),
                },
            }
        )
    return out


@router.get("/history/top-startups")
def pipeline_history_top_startups(
    limit: int = Query(30, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Append-only history of radar top-startup leaderboards (each pipeline completion)."""
    rows = (
        db.query(TopStartupsSnapshot)
        .order_by(TopStartupsSnapshot.captured_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for r in rows:
        try:
            entries = json.loads(r.entries_json or "[]")
        except json.JSONDecodeError:
            entries = []
        result.append(
            {
                "id": r.id,
                "captured_at": r.captured_at.isoformat() if r.captured_at else None,
                "pipeline_run_id": r.pipeline_run_id,
                "entries": entries,
            }
        )
    return result
