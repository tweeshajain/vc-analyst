"""
Find comparable companies via keyword similarity against other `Startup` rows,
supplemented with sector archetypes when the portfolio is thin.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from backend.app.models import Startup


@dataclass(frozen=True)
class PeerMatch:
    """One comparable for Competitive Landscape narrative."""

    name: str
    sector: str
    one_liner: str
    similarity: float
    origin: str  # "database" | "archetype"


_STOPWORDS = frozenset(
    """
    the and for with that this from have has had was were are been being
    their our your its his her they them their our out into over under
    but not you all can may will would could should about such than then
    when what which who how why into also just more most some any each
    both few other another same such only own same very just than then
    """.split()
)


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return float(inter) / float(union) if union else 0.0


def keyword_similarity(a: "Startup", b: "Startup") -> float:
    """Token overlap (Jaccard) on name, description, sector + small sector match bonus."""
    ta = _tokens(f"{a.name} {a.description} {a.sector}")
    tb = _tokens(f"{b.name} {b.description} {b.sector}")
    base = _jaccard(ta, tb)
    sa = (a.sector or "").strip().lower()
    sb = (b.sector or "").strip().lower()
    bonus = 0.15 if sa and sa == sb else 0.0
    return min(1.0, base + bonus)


def find_database_peers(
    startup: "Startup",
    db: Session,
    limit: int = 5,
) -> list[PeerMatch]:
    """Rank other startups in DB by keyword similarity; top `limit`."""
    from backend.app.models import Startup as StartupModel

    others = (
        db.query(StartupModel).filter(StartupModel.id != startup.id).all()
    )
    ranked: list[tuple["Startup", float]] = []
    for o in others:
        ranked.append((o, keyword_similarity(startup, o)))
    ranked.sort(key=lambda x: x[1], reverse=True)
    out: list[PeerMatch] = []
    for row, sim in ranked[:limit]:
        blurb = (row.description or "").strip()
        if len(blurb) > 160:
            blurb = blurb[:157] + "…"
        if not blurb:
            blurb = f"{row.source or 'portfolio'} listing; engagement radar {row.radar_score:.0f}."
        out.append(
            PeerMatch(
                name=row.name[:255],
                sector=(row.sector or "General")[:128],
                one_liner=blurb,
                similarity=round(sim, 3),
                origin="database",
            )
        )
    return out


# Generic buckets aligned with generator `_sector_bucket` themes
_ARCHETYPES: tuple[tuple[str, str], ...] = (
    (
        "Horizontal platform / suite incumbent",
        "Bundled distribution and IT budget gravity; slower roadmap wins on trust and coverage.",
    ),
    (
        "Best-of-breed workflow SaaS",
        "Opinionated UX in one department; expansion via integrations and seat growth.",
    ),
    (
        "AI/API infrastructure layer",
        "Model marketplaces and orchestration—commodity risk but massive attach surfaces.",
    ),
    (
        "Vertical specialist",
        "Deep compliance / domain moat in one industry; slower TAM but durable ACVs.",
    ),
    (
        "Open-source & community wedge",
        "Bottom-up adoption and developer mindshare; monetization via cloud/hosted tier.",
    ),
)


def _archetype_peers(count: int, seed: str) -> list[PeerMatch]:
    """Deterministic archetypes so outputs read like comparables without inventing fake brands."""
    if count <= 0:
        return []
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    picks: list[PeerMatch] = []
    n = len(_ARCHETYPES)
    for i in range(count):
        title, desc = _ARCHETYPES[(h + i) % n]
        picks.append(
            PeerMatch(
                name=title,
                sector="Market archetype",
                one_liner=desc,
                similarity=0.25,
                origin="archetype",
            )
        )
    return picks


def build_peer_set(
    startup: "Startup",
    db: Session | None,
    target_n: int = 5,
) -> list[PeerMatch]:
    """
    Combine DB similarity matches with archetypes to reach `target_n` (default 5).
    Prefer real portfolio rows first (keyword similarity), then pad with archetypes.
    """
    want = max(3, min(target_n, 5))
    db_peers: list[PeerMatch] = []
    if db is not None:
        db_peers = find_database_peers(startup, db, limit=want)

    need = want - len(db_peers)
    if need > 0:
        seed = f"{startup.id}-{startup.name}-comp"
        db_peers.extend(_archetype_peers(need, seed))

    # Trim to target_n if we over-filled (e.g. db returned 5 + archetypes)
    return db_peers[:want]
