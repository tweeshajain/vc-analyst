"""
CLI: fetch trending startups from Product Hunt + Reddit and store in SQLite.

Usage (from project root `ai-vc-analyst/`):

    python -m modules.radar.cli_fetch

Environment:
    PRODUCT_HUNT_TOKEN   — optional; without it, Product Hunt uses mock data.
    RADAR_WEIGHT_UPVOTES / RADAR_WEIGHT_COMMENTS — optional scoring weights.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def _bootstrap_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def main() -> int:
    _bootstrap_path()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from backend.app import models  # noqa: F401 — register models
    from backend.app.database import Base, SessionLocal, engine
    from backend.app.sqlite_migrate import ensure_startup_radar_columns
    from modules.radar.aggregator import fetch_all_trending
    from modules.radar.persistence import persist_trending_batch

    Base.metadata.create_all(bind=engine)
    ensure_startup_radar_columns(engine)

    items = fetch_all_trending()
    logging.getLogger(__name__).info("Fetched %s normalized records", len(items))
    db = SessionLocal()
    try:
        n = persist_trending_batch(db, items)
        print(f"Stored/updated {n} startup rows (upsert by source + external_id).")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
