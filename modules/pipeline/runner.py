"""
End-to-end daily pipeline: Radar fetch → rescore → memos → deal ranking snapshot.

Duplicate avoidance:
- Optional cooldown between full runs (default 60 min, overridable / `force`).
- Skips memo generation if a `generated` memo exists for the startup within 24h.
- Trending import uses existing upsert by (source, external_id).
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models import InvestmentMemo, PipelineRun, Startup, TopStartupsSnapshot
from modules.deals.deal_scoring import rank_investment_worthy
from modules.memo.generator import generate_memo
from modules.radar.aggregator import fetch_all_trending
from modules.radar.company_filter import startup_is_company_candidate
from modules.radar.persistence import persist_trending_batch
from modules.radar.ranking import build_top_startups_read
from modules.radar.scoring import compute_radar_score

log = logging.getLogger("ai_vc_analyst.pipeline")

PIPELINE_COOLDOWN_MINUTES = int(os.environ.get("PIPELINE_COOLDOWN_MINUTES", "60"))
PIPELINE_MEMO_LIMIT = int(os.environ.get("PIPELINE_MEMO_LIMIT", "40"))
MEMO_COOLDOWN_HOURS = int(os.environ.get("PIPELINE_MEMO_COOLDOWN_HOURS", "24"))
STALE_RUN_MINUTES = int(os.environ.get("PIPELINE_STALE_LOCK_MINUTES", "180"))


def _release_stale_running_runs(db: Session) -> int:
    """Mark long-running `running` rows as failed so a new run can start."""
    cutoff = datetime.utcnow() - timedelta(minutes=STALE_RUN_MINUTES)
    stuck = (
        db.query(PipelineRun)
        .filter(PipelineRun.status == "running", PipelineRun.started_at < cutoff)
        .all()
    )
    for r in stuck:
        r.status = "failed"
        r.finished_at = datetime.utcnow()
        r.error_message = "aborted: stale in-progress run"
    if stuck:
        db.commit()
    return len(stuck)


def _active_run(db: Session) -> PipelineRun | None:
    since = datetime.utcnow() - timedelta(minutes=STALE_RUN_MINUTES)
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.status == "running", PipelineRun.started_at >= since)
        .order_by(PipelineRun.started_at.desc())
        .first()
    )


def _last_completed_within(db: Session, minutes: int) -> PipelineRun | None:
    since = datetime.utcnow() - timedelta(minutes=minutes)
    return (
        db.query(PipelineRun)
        .filter(
            PipelineRun.status == "completed",
            PipelineRun.finished_at.isnot(None),
            PipelineRun.finished_at >= since,
        )
        .order_by(PipelineRun.finished_at.desc())
        .first()
    )


def should_skip_memo_generation(db: Session, startup_id: int) -> bool:
    """Avoid regenerating memos too frequently for the same company."""
    since = datetime.utcnow() - timedelta(hours=MEMO_COOLDOWN_HOURS)
    exists = (
        db.query(InvestmentMemo)
        .filter(
            InvestmentMemo.startup_id == startup_id,
            InvestmentMemo.status == "generated",
            InvestmentMemo.created_at >= since,
        )
        .first()
    )
    return exists is not None


def refresh_all_radar_scores(db: Session) -> int:
    """Recompute stored `radar_score` from engagement columns for every startup."""
    updated = 0
    for s in db.query(Startup).all():
        new_rs = compute_radar_score(s.upvotes, s.comments_count)
        if abs(float(s.radar_score) - new_rs) > 1e-6:
            s.radar_score = new_rs
            updated += 1
    db.commit()
    return updated


def run_daily_pipeline(
    db: Session,
    *,
    force: bool = False,
    cooldown_minutes: int | None = None,
    memo_limit: int | None = None,
    trigger: str = "api",
) -> dict[str, Any]:
    """
    1. Import trending startups (Product Hunt + Reddit) via Radar persistence.
    2. Refresh radar engagement scores for all rows.
    3. Generate investment memos (prioritize highest `radar_score`), respecting memo cooldown.
    4. Compute top deal ranking snapshot (scores stored in run stats JSON).

    Persists a `PipelineRun` row with `stats_json` unless skipped early.
    """
    cooldown = (
        cooldown_minutes if cooldown_minutes is not None else PIPELINE_COOLDOWN_MINUTES
    )
    mem_cap = memo_limit if memo_limit is not None else PIPELINE_MEMO_LIMIT

    _release_stale_running_runs(db)

    if not force:
        if _active_run(db):
            log.warning("Pipeline skipped: another run in progress")
            return {
                "status": "skipped",
                "reason": "another pipeline run is in progress",
            }
        recent = _last_completed_within(db, cooldown)
        if recent:
            log.info(
                "Pipeline skipped: cooldown (last finished %s)",
                recent.finished_at.isoformat() if recent.finished_at else "",
            )
            return {
                "status": "skipped",
                "reason": (
                    f"last completed run finished at {recent.finished_at.isoformat()} "
                    f"(cooldown {cooldown} min)"
                ),
                "run_id": recent.id,
            }

    log.info("Pipeline run starting trigger=%s", trigger)
    run = PipelineRun(status="running", started_at=datetime.utcnow(), trigger=trigger)
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id

    stats: dict[str, Any] = {"run_id": run_id}

    try:
        # 1 — Radar import
        log.info("Step 1/5: fetching trending sources")
        items = fetch_all_trending()
        n_import = persist_trending_batch(db, items)
        stats["trending_rows_processed"] = n_import
        stats["startups_in_db_after_import"] = db.query(Startup).count()
        log.info("Radar import done rows=%s", n_import)

        # 2 — Scoring
        log.info("Step 2/5: refreshing radar scores")
        n_refresh = refresh_all_radar_scores(db)
        stats["radar_scores_updated"] = n_refresh

        # 3 — Memos (prioritize traction; cap new memos per run)
        log.info("Step 3/5: memo generation (limit=%s)", mem_cap)
        candidates = (
            db.query(Startup)
            .order_by(Startup.radar_score.desc())
            .limit(max(mem_cap * 5, mem_cap))
            .all()
        )
        memos_created = 0
        memos_skipped_cooldown = 0
        for s in candidates:
            if memos_created >= mem_cap:
                break
            if should_skip_memo_generation(db, s.id):
                memos_skipped_cooldown += 1
                continue
            content = generate_memo(s, db)
            db.add(
                InvestmentMemo(
                    startup_id=s.id,
                    title=content.title,
                    summary=content.executive_summary,
                    status="generated",
                    company_overview=content.company_overview,
                    market_opportunity=content.market_opportunity,
                    business_model=content.business_model,
                    competitive_landscape=content.competitive_landscape,
                    differentiation_analysis=content.differentiation_analysis,
                    competitive_strengths=content.competitive_strengths,
                    competition=content.competition,
                    risks=content.risks,
                    investment_thesis=content.investment_thesis,
                )
            )
            memos_created += 1
        db.commit()
        stats["memos_created"] = memos_created
        stats["memos_skipped_recent_generated"] = memos_skipped_cooldown
        log.info(
            "Memos done created=%s skipped_cooldown=%s",
            memos_created,
            memos_skipped_cooldown,
        )

        # 4 — Deal ranking snapshot
        log.info("Step 4/5: deal ranking snapshot")
        pool = db.query(Startup).limit(600).all()
        pool = [s for s in pool if startup_is_company_candidate(s.source or "", s.name or "", s.url)]
        ranked = rank_investment_worthy(pool, limit=5)
        stats["top_deals"] = [
            {
                "startup_id": r.startup_id,
                "name": r.name,
                "score": r.deal_score,
                "stage": r.stage,
                "rationale": r.rationale,
                "why_it_matters": r.why_it_matters,
            }
            for r in ranked
        ]

        # 5 — Radar top-startups leaderboard + history row
        log.info("Step 5/5: radar top startups snapshot")
        pool_top = db.query(Startup).limit(800).all()
        top_startups = build_top_startups_read(pool_top, limit=10)
        stats["top_startups"] = [
            row.model_dump(mode="json") for row in top_startups
        ]
        db.add(
            TopStartupsSnapshot(
                captured_at=datetime.utcnow(),
                pipeline_run_id=run_id,
                entries_json=json.dumps(stats["top_startups"]),
            )
        )

        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.stats_json = json.dumps(stats)
        db.commit()

        log.info("Pipeline completed run_id=%s", run_id)
        out = {"status": "completed", **stats}
        return out

    except Exception as e:
        log.exception("Pipeline failed run_id=%s", run_id)
        run.status = "failed"
        run.finished_at = datetime.utcnow()
        run.error_message = f"{e}\n{traceback.format_exc()}"[:8000]
        run.stats_json = json.dumps({**stats, "error": str(e)})
        db.commit()
        raise
