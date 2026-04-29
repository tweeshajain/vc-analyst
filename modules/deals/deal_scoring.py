"""
Deal Finder scoring: combines radar engagement, VC keyword signals, and novelty
(how crowded a startup’s narrative is vs the rest of the portfolio).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from backend.app.models import Startup
from modules.memo.competitors import keyword_similarity
from modules.radar.scoring import keyword_boost_and_matches, min_max_normalize_0_100


Stage = Literal["early", "growth"]

# Blend weights (sum to 1.0)
W_ENGAGEMENT = 0.38
W_KEYWORDS = 0.32
W_NOVELTY = 0.30

_SIM_THRESHOLD = 0.14  # peers above this count as “similar pitch” cluster


def parse_industry_query(raw: str | None) -> str | None:
    """Normalize `industry` query param to AI | SaaS | health, or None if absent."""
    if raw is None or not str(raw).strip():
        return None
    k = str(raw).strip().lower()
    if k == "ai":
        return "AI"
    if k == "saas":
        return "SaaS"
    if k in ("health", "healthcare"):
        return "health"
    raise ValueError("industry must be one of: AI, SaaS, health")


def parse_stage_query(raw: str | None) -> str | None:
    """Normalize `stage` query param to pre-seed | seed, or None if absent."""
    if raw is None or not str(raw).strip():
        return None
    k = str(raw).strip().lower().replace("_", "-")
    if k in ("pre-seed", "preseed"):
        return "pre-seed"
    if k == "seed":
        return "seed"
    raise ValueError("stage must be one of: pre-seed, seed")


def startup_matches_industry(s: Startup, canonical: str) -> bool:
    """Match startup text to industry bucket (name, sector, description)."""
    blob = f"{s.name} {s.sector} {s.description}".lower()
    if canonical == "AI":
        if re.search(r"\bai\b", blob):
            return True
        if re.search(r"\bml\b", blob) or re.search(r"\bllm\b", blob):
            return True
        return any(
            x in blob
            for x in (
                "machine learning",
                "deep learning",
                "gpt",
                "generative",
                "neural",
                "transformer",
            )
        )
    if canonical == "SaaS":
        if "saas" in blob:
            return True
        if "software-as-a-service" in blob:
            return True
        return ("b2b" in blob or "enterprise" in blob) and "software" in blob
    if canonical == "health":
        return any(
            x in blob
            for x in (
                "health",
                "healthcare",
                "medical",
                "clinical",
                "patient",
                "biotech",
                "diagnostic",
                "pharma",
                "fda",
            )
        )
    return False


def startup_matches_funding_stage_filter(s: Startup, canonical: str) -> bool:
    """Filter by labels stored on `Startup.stage` (pre-seed vs seed)."""
    raw = (s.stage or "").lower()
    if canonical == "pre-seed":
        return any(x in raw for x in ("pre-seed", "preseed", "pre seed", "angel"))
    if canonical == "seed":
        if any(x in raw for x in ("pre-seed", "preseed", "pre seed")):
            return False
        return "seed" in raw
    return False


def filter_startups_for_top_deals(
    startups: list[Startup],
    industry: str | None,
    funding_stage: str | None,
) -> list[Startup]:
    out = startups
    if industry:
        out = [x for x in out if startup_matches_industry(x, industry)]
    if funding_stage:
        out = [x for x in out if startup_matches_funding_stage_filter(x, funding_stage)]
    return out


@dataclass(frozen=True)
class DealScoreBreakdown:
    startup_id: int
    name: str
    deal_score: float
    stage: Stage
    rationale: str
    why_it_matters: str


def _infer_stage(s: Startup) -> Stage:
    """Map stored stage + traction heuristics to early vs growth."""
    st = (s.stage or "").lower()
    if any(
        x in st
        for x in (
            "series b",
            "series c",
            "series d",
            "series e",
            "growth",
            "late",
            "public",
        )
    ):
        return "growth"
    if "series a" in st and (s.radar_score >= 80 or s.upvotes >= 120):
        return "growth"
    if s.radar_score >= 600 or (s.upvotes >= 400 and s.comments_count >= 40):
        return "growth"
    return "early"


def _novelty_raw(startup: Startup, pool: list[Startup]) -> float:
    """
    Higher when few peers look textually similar (less “repeated idea” crowding).
    Returns roughly 0–100 before normalization across the batch.
    """
    close = 0
    for o in pool:
        if o.id == startup.id:
            continue
        if keyword_similarity(startup, o) >= _SIM_THRESHOLD:
            close += 1
    return 100.0 / (1.0 + 1.25 * close)


def _rationale_line(
    eng_n: float,
    kw_labels: list[str],
    nov_n: float,
    stage: Stage,
) -> str:
    """Single readable line for investors."""
    if eng_n >= 0.66:
        eng_phrase = "Strong radar engagement"
    elif eng_n >= 0.33:
        eng_phrase = "Solid engagement"
    else:
        eng_phrase = "Early/modest engagement"

    if kw_labels:
        kw_phrase = f"signals: {', '.join(kw_labels[:4])}"
    else:
        kw_phrase = "no keyword spike terms detected"

    if nov_n >= 0.55:
        nov_phrase = "more differentiated narrative vs portfolio peers"
    elif nov_n >= 0.3:
        nov_phrase = "average novelty—some similar pitches exist"
    else:
        nov_phrase = "crowded/similar narratives in dataset—extra differentiation needed"

    return (
        f"{eng_phrase}; {kw_phrase}; {nov_phrase}; "
        f"{stage}-stage profile for screening."
    )[:280]


def _why_it_matters(
    deal_score: float,
    stage: Stage,
    eng_n: float,
    kw_labels: list[str],
    name: str,
) -> str:
    """
    Short portfolio takeaway for demos: why this opportunity deserves attention
    beyond raw score (mandate fit, timing, traction tier).
    """
    nm = (name or "This company").strip()[:60]
    parts: list[str] = []

    if deal_score >= 72:
        parts.append(
            f"{nm} ranks near the top of the current funnel—worth a fast partner sync "
            "to align on diligence depth and capacity."
        )
    elif deal_score >= 55:
        parts.append(
            f"{nm} sits in the actionable band: strong enough to justify outreach "
            "while keeping IC expectations realistic."
        )
    else:
        parts.append(
            f"{nm} is a watchlist candidate—useful for theme mapping even if "
            "immediate priority is lower."
        )

    if stage == "growth":
        parts.append(
            "Growth-stage profile: prioritize commercial validation and "
            "scalability evidence in the next conversation."
        )
    else:
        parts.append(
            "Early-stage profile: focus on team velocity, clarity of wedge, and "
            "near-term milestones—not just hype."
        )

    if eng_n >= 0.55:
        parts.append("Market pull looks credible from engagement signals in our dataset.")
    elif eng_n <= 0.2:
        parts.append(
            "Engagement is still emerging—pair narrative diligence with a crisp "
            "plan to manufacture proof points."
        )

    if kw_labels:
        top_kw = ", ".join(kw_labels[:3])
        parts.append(f"Keyword fit highlights: {top_kw}—maps cleanly to active thesis tags.")

    out = " ".join(parts)
    return out[:398]


def rank_investment_worthy(
    startups: list[Startup],
    limit: int = 5,
) -> list[DealScoreBreakdown]:
    """
    Compute deal_score (0–100) from normalized engagement, keywords, novelty.
    Returns top `limit` rows sorted by deal_score descending.
    """
    if not startups:
        return []

    pool = list(startups)
    eng_raw = [float(s.radar_score) for s in pool]
    kw_raw: list[float] = []
    kw_labels_per: list[list[str]] = []
    nov_raw: list[float] = []

    for s in pool:
        boost, labels = keyword_boost_and_matches(f"{s.name}\n{s.description}")
        kw_raw.append(boost)
        kw_labels_per.append(labels)
        nov_raw.append(_novelty_raw(s, pool))

    eng_n = min_max_normalize_0_100(eng_raw)
    kw_n = min_max_normalize_0_100(kw_raw)
    nov_n = min_max_normalize_0_100(nov_raw)

    rows: list[tuple[float, Startup, float, float, float, list[str]]] = []
    for i, s in enumerate(pool):
        combined = (
            W_ENGAGEMENT * (eng_n[i] / 100.0)
            + W_KEYWORDS * (kw_n[i] / 100.0)
            + W_NOVELTY * (nov_n[i] / 100.0)
        )
        deal_score = round(min(100.0, max(0.0, combined * 100.0)), 2)
        rows.append(
            (
                deal_score,
                s,
                eng_n[i] / 100.0,
                kw_n[i] / 100.0,
                nov_n[i] / 100.0,
                kw_labels_per[i],
            )
        )

    rows.sort(key=lambda x: x[0], reverse=True)

    out: list[DealScoreBreakdown] = []
    for deal_score, s, e_norm, _kn, nov_norm, labels in rows[:limit]:
        stage = _infer_stage(s)
        rationale = _rationale_line(e_norm, labels, nov_norm, stage)
        why = _why_it_matters(deal_score, stage, e_norm, labels, s.name)
        out.append(
            DealScoreBreakdown(
                startup_id=s.id,
                name=s.name,
                deal_score=deal_score,
                stage=stage,
                rationale=rationale,
                why_it_matters=why,
            )
        )
    return out
