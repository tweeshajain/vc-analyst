"""
Aggregate recurring themes across startups (name, sector, description).
Demo-ready keyword buckets with counts and example companies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.models import Startup


@dataclass(frozen=True)
class ThemeRule:
    label: str
    description: str
    pattern: re.Pattern[str]


def theme_rules() -> tuple[ThemeRule, ...]:
    return (
        ThemeRule(
            "AI & machine learning",
            "LLMs, ML platforms, and applied intelligence",
            re.compile(
                r"\b(ai|ml|llm|gpt|machine learning|deep learning|neural|"
                r"generative|copilot|embedding|transformer)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Automation & workflows",
            "Process automation, orchestration, and ops efficiency",
            re.compile(
                r"\b(automation|workflow|orchestrat|pipeline|no-?code|"
                r"low-?code|rpa|agent)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Developer tools & infra",
            "APIs, observability, cloud, and engineering productivity",
            re.compile(
                r"\b(devops|api|sdk|observability|kubernetes|docker|"
                r"infrastructure|backend|git|ci/cd)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "SaaS & B2B software",
            "Subscription software, enterprise, and vertical SaaS",
            re.compile(
                r"\b(saas|b2b|enterprise|subscription|crm|erp|salesforce)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Growth & revenue",
            "GTM, monetization, and scaling narratives",
            re.compile(
                r"\b(growth|revenue|monetiz|gtm|sales|marketing|conversion|"
                r"retention|arr)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Fintech & payments",
            "Money movement, lending, banking, and compliance",
            re.compile(
                r"\b(fintech|payment|lending|banking|ledger|treasury|"
                r"compliance|kyc|fraud)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Healthcare & bio",
            "Clinical, diagnostics, and health tech",
            re.compile(
                r"\b(health|healthcare|medical|clinical|patient|bio|"
                r"diagnostic|fda|pharma|drug)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Climate & sustainability",
            "Energy transition, carbon, and cleantech",
            re.compile(
                r"\b(climate|carbon|clean|energy|solar|battery|esg|"
                r"sustainab|grid)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Security & privacy",
            "Cybersecurity, identity, and data protection",
            re.compile(
                r"\b(security|cyber|zero trust|identity|sso|encryption|"
                r"privacy|soc2)\b",
                re.I,
            ),
        ),
        ThemeRule(
            "Productivity & collaboration",
            "Team workflows, docs, and communication",
            re.compile(
                r"\b(productivity|collaboration|workspace|docs|notion|"
                r"slack|chat|meeting)\b",
                re.I,
            ),
        ),
    )


def _blob(s: Startup) -> str:
    return f"{s.name}\n{s.sector}\n{s.description}"


def build_trends(startups: list[Startup]) -> tuple[list[dict], str, int]:
    """
    Returns (theme rows for API), headline sentence, pool size.
    Each theme row: label, description, count, share, examples (names).
    """
    rules = theme_rules()
    pool = list(startups)
    n = len(pool)
    if n == 0:
        return [], "No startups in the database yet—run the pipeline or add companies.", 0

    per_theme: list[tuple[ThemeRule, int, list[str]]] = []
    for rule in rules:
        matched = [s for s in pool if rule.pattern.search(_blob(s))]
        cnt = len(matched)
        names = [s.name[:80] for s in matched[:4]]
        per_theme.append((rule, cnt, names))

    per_theme.sort(key=lambda x: x[1], reverse=True)
    rows: list[dict] = []
    for rule, cnt, examples in per_theme:
        if cnt == 0:
            continue
        share = round(cnt / n, 3)
        rows.append(
            {
                "label": rule.label,
                "description": rule.description,
                "count": cnt,
                "share": share,
                "examples": examples[:3],
            }
        )

    top = rows[:6]
    if not top:
        headline = (
            f"Analyzed {n} startups—no strong keyword clusters yet; "
            "enrich descriptions for richer trends."
        )
    else:
        lead = top[0]
        second = top[1] if len(top) > 1 else None
        headline = (
            f"{lead['label']} shows up in {lead['count']} of {n} companies "
            f"({int(round(lead['share'] * 100))}%)."
        )
        if second and second["count"] >= max(2, n // 10):
            headline += f" Next: {second['label']} ({second['count']} mentions)."

    return top, headline, n
