"""Leaderboard: dedupe startups, composite ranking, normalized scores, reasons."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.models import Startup
from backend.app.schemas import TopStartupRead
from modules.radar.company_filter import startup_is_company_candidate
from modules.radar.scoring import (
    RankingBreakdown,
    compute_ranking_breakdown,
    build_short_ranking_reason,
    min_max_normalize_0_100,
)


def _sector_label(raw: str) -> str:
    s = (raw or "").strip()
    return s if s else "General"


def _stage_label(raw: str) -> str:
    s = (raw or "").strip()
    return s if s else "Unspecified"


def build_radar_insight_line(b: RankingBreakdown, sector_guess: str) -> str:
    """
    Single-line, analyst-style takeaway derived from signals (template-based “AI” voice).
    """
    sector = _sector_label(sector_guess)
    if b.engagement >= 120 or b.raw_score >= 200:
        tier_desc = "Outsized community pull"
    elif b.engagement >= 40:
        tier_desc = "Solid engagement momentum"
    else:
        tier_desc = "Early visibility"

    if b.matched_keywords:
        lead = b.matched_keywords[0]
        rest = len(b.matched_keywords) - 1
        tail = f" (+{rest} related signals)" if rest else ""
        line = (
            f"{tier_desc} with {lead} narrative fit{tail} — "
            f"{sector} positioning is resonating in-channel."
        )
    else:
        line = (
            f"{tier_desc}; pure traction read in-feed — {sector} angle merits "
            f"a fast screen before the narrative crowds."
        )
    return line[:198]


def norm_score_to_vc_relevance_10(norm: float) -> int:
    """Map 0–100 normalized leaderboard score to VC relevance 1–10."""
    n = int(round(float(norm) / 100.0 * 9)) + 1
    return max(1, min(10, n))


def build_why_qualifies_short(insight: str, ranking_reason: str, max_chars: int = 260) -> str:
    """Single block for digest; trimmed to ~2 lines."""
    parts = [p.strip() for p in (insight, ranking_reason) if (p or "").strip()]
    text = " ".join(parts)
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def build_vc_digest(
    name: str,
    sector: str,
    stage: str,
    qualifies: str,
    relevance_1_10: int,
) -> str:
    """Strict five-field output for UI / export."""
    sec = _sector_label(sector)
    stg = _stage_label(stage)
    return (
        f"Company Name: {name}\n"
        f"Sector: {sec}\n"
        f"Stage: {stg}\n"
        f"Why it qualifies (1–2 lines max): {qualifies}\n"
        f"VC relevance score (1–10): {relevance_1_10}"
    )


def build_radar_why_it_matters(
    name: str,
    normalized_score: float,
    sector_raw: str,
    stage_raw: str,
    matched: tuple[str, ...],
) -> str:
    """Why this name deserves bandwidth vs the rest of the funnel this week."""
    sector = _sector_label(sector_raw)
    stage = _stage_label(stage_raw)
    nm = (name or "This company").strip()[:48]
    if normalized_score >= 75:
        pri = f"{nm} sits in the top decile of this radar slice—allocate partner time for a crisp next step."
    elif normalized_score >= 45:
        pri = f"{nm} is squarely in the active queue: enough signal to justify outreach while expectations stay disciplined."
    else:
        pri = f"{nm} is a watchlist name—track for theme intelligence even if near-term priority is lower."

    kw_bit = (
        f" Keyword alignment ({', '.join(matched[:3])}) maps to live thesis tags."
        if matched
        else " Lead with velocity proof points—the profile is still proving category drag."
    )
    stage_bit = f" Label reads as {stage}; validate {sector} wedge depth on the first call."
    out = f"{pri} {stage_bit}{kw_bit}"
    return out[:398]


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
    rows = [
        s
        for s in rows
        if startup_is_company_candidate(s.source or "", s.name or "", s.url)
    ]
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
        insight = build_radar_insight_line(b, row.sector or "")
        why = build_radar_why_it_matters(
            row.name,
            float(norm),
            row.sector or "",
            row.stage or "",
            b.matched_keywords,
        )
        rel10 = norm_score_to_vc_relevance_10(float(norm))
        qualifies = build_why_qualifies_short(insight, reason)
        digest = build_vc_digest(
            row.name or "",
            row.sector or "",
            row.stage or "",
            qualifies,
            rel10,
        )
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
                sector=row.sector or "",
                stage=row.stage or "",
                insight=insight,
                why_it_matters=why,
                vc_digest=digest[:900],
            )
        )
    return out
