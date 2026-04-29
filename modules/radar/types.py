"""Shared datatypes for ingesting external trending data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendingStartup:
    """Normalized record from Product Hunt, Reddit, or other sources."""

    name: str
    description: str
    url: str
    upvotes: int
    comments_count: int
    source: str
    external_id: str
    sector: str = ""
    stage: str = ""
