"""Leaderboard: dedupe startups, composite ranking, normalized scores, reasons."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.models import Startup
from backend.app.schemas import TopStartupRead
from modules.radar.scoring import (
    RankingBreakdown,
    compute_ranking_breakdown,
    build_short_ranking_reason,
    min_max_normalize_0_100,
)


_REDDIT_HOSTS = frozenset(
    {"reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com"}
)
_PRODUCT_HUNT_HOST = "producthunt.com"


def canonical_dedupe_key(name: str, url: str) -> str:
    """
    Prefer registrable domain when URL is specific; otherwise normalized title.
    Reddit/Product Hunt listing URLs collapse to name-based keys so threads don't
    all dedupe to one host.
    """
    raw = (url or "").strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or "").lower().removeprefix("www.")
    path_l = (parsed.path or "").lower()

    if host and host not in _REDDIT_HOSTS and _PRODUCT_HUNT_HOST not in host:
        return f"host:{host}"

    if host and _PRODUCT_HUNT_HOST in host and "/posts/" in path_l:
        slug = path_l.rstrip("/").split("/posts/")[-1].split("/")[0]
        if slug:
            return f"ph_slug:{slug.lower()}"

    n = re.sub(r"[^\w\s]+", " ", (name or "").lower())
    n = re.sub(r"\s+", " ", n).strip()[:96]
    return f"name:{n}"


@dataclass(frozen=True)
class _Enriched:
    breakdown: RankingBreakdown
    row: Startup


def _enrich(row: Startup) -> _Enriched:
    b = compute_ranking_breakdown(
        row.name,
        row.description or "",
        row.upvotes,
        row.comments_count,
    )
    return _Enriched(breakdown=b, row=row)


def dedupe_by_best_raw(enriched: list[_Enriched]) -> list[_Enriched]:
    """Keep one row per dedupe key — the highest raw_score wins."""
    best: dict[str, _Enriched] = {}
    for e in enriched:
        key = canonical_dedupe_key(e.row.name, e.row.url or "")
        prev = best.get(key)
        if prev is None or e.breakdown.raw_score > prev.breakdown.raw_score:
            best[key] = e
    return list(best.values())


def build_top_startups_read(
    startups: list[Startup],
    limit: int = 10,
    candidate_cap: int = 800,
) -> list[TopStartupRead]:
    """
    Rank all (capped) startups, dedupe, take top `limit` by raw composite score,
    normalize scores to 0–100 across that top slice only.
    """
    rows = startups[:candidate_cap] if len(startups) > candidate_cap else startups
    enriched = [_enrich(s) for s in rows]
    deduped = dedupe_by_best_raw(enriched)
    deduped.sort(key=lambda e: e.breakdown.raw_score, reverse=True)
    top_slice = deduped[:limit]
    raws = [e.breakdown.raw_score for e in top_slice]
    norms = min_max_normalize_0_100(raws)

    out: list[TopStartupRead] = []
    for e, norm in zip(top_slice, norms):
        row = e.row
        b = e.breakdown
        reason = build_short_ranking_reason(b, norm)
        out.append(
            TopStartupRead(
                id=row.id,
                name=row.name,
                description=row.description or "",
                url=row.url or "",
                source=row.source,
                upvotes=row.upvotes,
                comments_count=row.comments_count,
                radar_score=float(row.radar_score),
                score=round(float(norm), 4),
                ranking_reason=reason,
                created_at=row.created_at,
            )
        )
    return out
