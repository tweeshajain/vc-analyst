"""Persist normalized trending records into the `startups` table."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models import Startup
from modules.radar.scoring import compute_radar_score
from modules.radar.types import TrendingStartup


def upsert_trending(db: Session, item: TrendingStartup) -> Startup:
    """Insert or update by (source, external_id); refreshes engagement + radar_score."""
    radar_score = compute_radar_score(item.upvotes, item.comments_count)
    existing = (
        db.query(Startup)
        .filter(
            Startup.source == item.source,
            Startup.external_id == item.external_id,
        )
        .first()
    )
    if existing:
        existing.name = item.name[:255]
        existing.description = item.description
        existing.url = item.url[:2048]
        existing.upvotes = item.upvotes
        existing.comments_count = item.comments_count
        existing.radar_score = radar_score
        if item.sector:
            existing.sector = item.sector[:128]
        if item.stage:
            existing.stage = item.stage[:64]
        return existing

    row = Startup(
        name=item.name[:255],
        description=item.description,
        url=item.url[:2048],
        source=item.source,
        external_id=item.external_id,
        upvotes=item.upvotes,
        comments_count=item.comments_count,
        radar_score=radar_score,
        sector=(item.sector or "")[:128],
        stage=(item.stage or "")[:64],
    )
    db.add(row)
    return row


def persist_trending_batch(db: Session, items: list[TrendingStartup]) -> int:
    """Upsert all items and commit once. Returns number of rows processed."""
    for item in items:
        upsert_trending(db, item)
    db.commit()
    return len(items)
