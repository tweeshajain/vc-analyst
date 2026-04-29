"""Radar scoring: engagement weights, keyword signal boosts, normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Iterable


@dataclass(frozen=True)
class EngagementWeights:
    """Weights for combining engagement metrics."""

    upvotes: float = 1.0
    comments: float = 2.0


@dataclass(frozen=True)
class KeywordSignal:
    """High-signal term with an additive boost (applied once per term if matched)."""

    label: str
    pattern: re.Pattern[str]
    boost: float


def load_weights_from_env() -> EngagementWeights:
    u = float(os.environ.get("RADAR_WEIGHT_UPVOTES", "1.0"))
    c = float(os.environ.get("RADAR_WEIGHT_COMMENTS", "2.0"))
    return EngagementWeights(upvotes=u, comments=c)


def default_keyword_signals() -> tuple[KeywordSignal, ...]:
    """Curated terms that often correlate with investable / trending B2B narratives."""
    return (
        KeywordSignal("AI", re.compile(r"\bAI\b", re.I), 18.0),
        KeywordSignal(
            "automation", re.compile(r"\bautomation\b", re.I), 14.0
        ),
        KeywordSignal("growth", re.compile(r"\bgrowth\b", re.I), 12.0),
        KeywordSignal("revenue", re.compile(r"\brevenue\b", re.I), 14.0),
    )


def compute_radar_score(
    upvotes: int,
    comments_count: int,
    weights: EngagementWeights | None = None,
) -> float:
    """Weighted sum of engagement only (stored as `radar_score` in DB)."""
    w = weights or load_weights_from_env()
    return float(w.upvotes) * max(0, upvotes) + float(w.comments) * max(
        0, comments_count
    )


def keyword_boost_and_matches(
    text: str,
    signals: Iterable[KeywordSignal] | None = None,
) -> tuple[float, list[str]]:
    """
    Sum boosts for each distinct signal that matches `text` (name + description).
    Returns (total_boost, matched labels in stable order).
    """
    sigs = tuple(signals) if signals is not None else default_keyword_signals()
    hay = text or ""
    total = 0.0
    matched: list[str] = []
    for s in sigs:
        if s.pattern.search(hay):
            total += s.boost
            matched.append(s.label)
    return total, matched


@dataclass(frozen=True)
class RankingBreakdown:
    """Components used for ranking and explaining the result."""

    engagement: float
    keyword_boost: float
    matched_keywords: tuple[str, ...]
    raw_score: float


def compute_ranking_breakdown(
    name: str,
    description: str,
    upvotes: int,
    comments_count: int,
    weights: EngagementWeights | None = None,
    signals: Iterable[KeywordSignal] | None = None,
) -> RankingBreakdown:
    """Raw ranking score = engagement + keyword boosts (not normalized)."""
    eng = compute_radar_score(upvotes, comments_count, weights)
    boost, labels = keyword_boost_and_matches(
        f"{name}\n{description}", signals=signals
    )
    raw = eng + boost
    return RankingBreakdown(
        engagement=eng,
        keyword_boost=boost,
        matched_keywords=tuple(labels),
        raw_score=raw,
    )


def min_max_normalize_0_100(values: list[float]) -> list[float]:
    """Scale values into [0, 100]; identical values map to 100."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [100.0 for _ in values]
    return [100.0 * (v - lo) / (hi - lo) for v in values]


def build_short_ranking_reason(
    b: RankingBreakdown,
    normalized_score: float,
) -> str:
    """Short text for clients: why this row landed where it did on the board."""
    ns = f"{normalized_score:.0f}/100"
    if b.keyword_boost > 0 and b.matched_keywords:
        kw = ", ".join(b.matched_keywords)
        text = (
            f"High engagement; boosted for signals: {kw} "
            f"(+{b.keyword_boost:.0f}). Composite raw {b.raw_score:.0f} -> {ns}."
        )
    else:
        text = (
            f"Driven by engagement (votes & comments), raw {b.raw_score:.0f} -> {ns}."
        )
    if len(text) > 240:
        text = text[:237] + "…"
    return text
