"""Background cron: daily pipeline without manual triggers."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.app.database import SessionLocal

log = logging.getLogger("ai_vc_analyst.pipeline.scheduler")

SCHEDULER_ENABLED = os.environ.get("PIPELINE_SCHEDULER_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)


def _scheduled_pipeline_job() -> None:
    """Runs inside APScheduler worker thread."""
    log.info("Scheduled pipeline job starting")
    db = SessionLocal()
    try:
        from modules.pipeline.runner import run_daily_pipeline

        result = run_daily_pipeline(
            db,
            force=False,
            cooldown_minutes=0,
            trigger="scheduler",
        )
        log.info(
            "Scheduled pipeline finished: status=%s run_id=%s",
            result.get("status"),
            result.get("run_id"),
        )
    except Exception:
        log.exception("Scheduled pipeline failed")
    finally:
        db.close()


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler | None:
    """Start UTC cron job; returns None if disabled via env."""
    global _scheduler
    if not SCHEDULER_ENABLED:
        log.info("PIPELINE_SCHEDULER_ENABLED=false — daily cron not started")
        return None
    if _scheduler is not None:
        return _scheduler

    hour = int(os.environ.get("PIPELINE_SCHEDULE_HOUR_UTC", "6"))
    minute = int(os.environ.get("PIPELINE_SCHEDULE_MINUTE", "0"))

    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(
        _scheduled_pipeline_job,
        CronTrigger(hour=hour, minute=minute),
        id="daily_pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    _scheduler = sched
    log.info(
        "APScheduler started: daily pipeline at %02d:%02d UTC",
        hour,
        minute,
    )
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        log.info("APScheduler shut down")
        _scheduler = None