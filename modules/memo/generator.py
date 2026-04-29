"""
Investment memo generation — structured VC-style narrative.

Uses deterministic, template-augmented prose (simulated “LLM-style” reasoning)
from startup attributes so results work offline without external API keys.

Competitive intelligence blends keyword similarity against portfolio DB rows and
sector archetypes when peer coverage is thin.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from modules.memo.competitors import PeerMatch, build_peer_set

if TYPE_CHECKING:
    from backend.app.models import Startup


@dataclass(frozen=True)
class StructuredMemo:
    """Sections returned by `generate_memo` and persisted on `InvestmentMemo`."""

    title: str
    executive_summary: str
    company_overview: str
    market_opportunity: str
    business_model: str
    competitive_landscape: str
    differentiation_analysis: str
    competitive_strengths: str
    competition: str
    risks: str
    investment_thesis: str


def _clean(text: str, limit: int = 1200) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) > limit:
        return t[: limit - 1].rsplit(" ", 1)[0] + "…"
    return t


def _sector_bucket(sector: str, description: str) -> str:
    blob = f"{sector} {description}".lower()
    if any(k in blob for k in ("ai", "ml", "llm", "machine learning")):
        return "applied AI / intelligent automation"
    if "fintech" in blob or "payments" in blob:
        return "financial technology"
    if "health" in blob or "medical" in blob or "bio" in blob:
        return "healthcare technology"
    if "saas" in blob or "enterprise" in blob:
        return "B2B SaaS"
    return (sector or "technology").strip() or "technology"


def _stage_line(stage: str) -> str:
    s = (stage or "").strip()
    if not s:
        return "an early-stage private company"
    return f"a {s}-stage private company"


def _format_competitive_landscape(peers: list[PeerMatch], bucket: str) -> str:
    intro = (
        f"Comparable references for **{bucket}**, ranked by keyword overlap on name, "
        "description, and sector versus other tracked startups, supplemented with "
        "representative market archetypes when the portfolio yields fewer than five anchors."
    )
    blocks: list[str] = [intro, ""]
    for i, p in enumerate(peers, 1):
        tag = "Portfolio similarity (database)" if p.origin == "database" else "Archetype (benchmark)"
        sim = (
            f" Similarity index {p.similarity:.2f}."
            if p.origin == "database"
            else ""
        )
        blocks.append(
            f"{i}. **{p.name}** — _{p.sector}_ · {tag}.{sim} {p.one_liner}"
        )
    return "\n".join(blocks)


def _differentiation_block(
    name: str,
    bucket: str,
    peers: list[PeerMatch],
) -> str:
    db_names = [p.name for p in peers if p.origin == "database"]
    arche_names = [p.name for p in peers if p.origin == "archetype"]
    peer_sentence = ""
    if db_names:
        peer_sentence = (
            f" Relative to keyword-matched portfolio names ({', '.join(db_names[:4])}), "
            f"{name} should articulate wedge-specific workflows—not horizontal breadth—as the primary hook."
        )
    elif arche_names:
        peer_sentence = (
            f" Versus common archetypes ({arche_names[0]}, …), "
            f"{name} wins by owning a crisp workflow slice with measurable ROI proof points."
        )
    else:
        peer_sentence = (
            f"{name} must anchor differentiation on workflow depth, integration posture, "
            "and time-to-value—not generic AI claims."
        )

    body = (
        f"{peer_sentence} "
        f"In {bucket}, buyers reward vendors who compress implementation cycles, "
        "expose ROI dashboards early, and ship reliability before novelty. "
        f"A credible roadmap shows land-and-expand within one department before "
        "cross-selling platform promises."
    )
    return _clean(body, 1600)


def _strengths_block(name: str, bucket: str, peers: list[PeerMatch]) -> str:
    vs = [
        "Speed of iteration vs bundled suite roadmap cadence.",
        "Focus vs horizontal platforms that optimize for average workflows.",
        "Implementation lightness vs legacy SI-heavy deployments.",
    ]
    if any(p.origin == "database" for p in peers):
        vs.append(
            "Narrative clarity vs keyword-adjacent startups competing for the same SEO story."
        )
    bullets = "\n".join(f"- {x}" for x in vs)
    return _clean(
        f"Potential strengths for **{name}** in **{bucket}** versus the comparable set:\n{bullets}",
        1400,
    )


def generate_memo(startup: "Startup", db: Session | None = None) -> StructuredMemo:
    """
    Produce a structured memo from a Startup ORM row.

    When `db` is provided, peer discovery uses other `Startup` rows plus archetypes.
    """
    name = (startup.name or "Company").strip()
    sector_raw = (startup.sector or "").strip()
    stage = (startup.stage or "").strip()
    desc = _clean(startup.description or "", 600)
    url = (startup.url or "").strip()
    bucket = _sector_bucket(sector_raw, desc)
    stage_phrase = _stage_line(stage)

    peers = build_peer_set(startup, db, target_n=5)

    web = f" Web presence: {url}." if url else ""

    company_overview = (
        f"{name} is {stage_phrase} building in {bucket}. "
        f"{desc if desc else 'Public materials emphasize product-led traction and iterative go-to-market execution.'}"
        f"{web} "
        "From available signals, the team appears focused on delivering a differentiated wedge into an "
        "underserved workflow before expanding platform scope."
    )

    market_opportunity = (
        f"The addressable need sits at the intersection of {bucket} adoption and operational efficiency: "
        "buyers are consolidating vendors, prioritizing measurable ROI, and seeking solutions that embed "
        "into existing stacks without heavy professional services. "
        "Macro uncertainty tends to lengthen sales cycles but also accelerates replacement purchases where "
        "incumbents fail on flexibility or time-to-value. "
        f"If {name} can anchor a narrow ICP with repeatable discovery → pilot → expansion, "
        "there is room to compound within mid-market and enterprise budgets over multiple years."
    )

    business_model = (
        "The likely monetization path follows recurring revenue—subscriptions and/or usage-based pricing—"
        "with expansion driven by seats, workflows, or data volume. "
        "Gross margin profile in software can be strong if hosting and model inference costs are bounded; "
        "key diligence themes include net retention, payback period, and sales efficiency (e.g., magic number). "
        f"For {name}, prioritizing a crisp pricing metric aligned to customer value (time saved, revenue uplift, "
        "risk reduced) should improve conversion and reduce churn in competitive bake-offs."
    )

    competitive_landscape = _clean(_format_competitive_landscape(peers, bucket), 3200)

    differentiation_analysis = _differentiation_block(name, bucket, peers)

    competitive_strengths = _strengths_block(name, bucket, peers)

    competition = (
        f"Beyond named comparables, {name} operates where horizontal suites, vertical SaaS specialists, "
        f"and infra/API vendors all intersect in {bucket}. "
        "Incumbents monetize breadth; challengers monetize depth—pipeline risk spikes when buyers "
        "issue broad RFPs that favor checklist parity. Mitigate with crisp proof assets (pilots, ROI math, "
        "security posture) and explicit kill criteria versus suites."
    )

    risks = (
        "Key risks include (1) execution against a crowded narrative—clarity of ICP and roadmap sequencing; "
        "(2) sales/market risk if budgets tighten or procurement slows; "
        "(3) technical/model risk if reliability, safety, or compliance requirements outpace product maturity; "
        "(4) financing risk if runway does not match the planned hiring and GTM ramp. "
        "Mitigants are disciplined experimentation, measurable pilots, and conservative burn relative to pipeline coverage."
    )

    thesis = (
        f"We would underwrite {name} if diligence confirms durable adoption signals within a wedge customer profile, "
        "healthy cohort economics, and a credible path to expand ACVs without heroic services. "
        "The upside case is category leadership within a defined workflow; the downside case is feature replication "
        "by platforms—mitigated by distribution pace, switching costs, and proprietary workflow/data advantages. "
        "Recommended next steps: founder references, customer calls, technical architecture review, competitive "
        "win/loss review against the comparable set above, and commercial deep dive."
    )

    exec_sum = _clean(
        f"{name} ({bucket}) — {stage_phrase}; memo includes keyword-informed competitive landscape, "
        "differentiation view, and strengths vs peers alongside standard diligence framing.",
        360,
    )

    title = f"{name} — Investment Memo"

    return StructuredMemo(
        title=title,
        executive_summary=exec_sum,
        company_overview=_clean(company_overview, 1400),
        market_opportunity=_clean(market_opportunity, 1400),
        business_model=_clean(business_model, 1400),
        competitive_landscape=competitive_landscape,
        differentiation_analysis=differentiation_analysis,
        competitive_strengths=competitive_strengths,
        competition=_clean(competition, 1400),
        risks=_clean(risks, 1400),
        investment_thesis=_clean(thesis, 1400),
    )
