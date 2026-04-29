"""Aggregate trending items from all configured sources."""

from __future__ import annotations

from modules.radar.sources import product_hunt, reddit
from modules.radar.types import TrendingStartup


def fetch_all_trending(
    ph_first: int = 15,
    reddit_limit: int = 15,
) -> list[TrendingStartup]:
    """Pull Product Hunt and Reddit listings into one normalized list."""
    items: list[TrendingStartup] = []
    items.extend(product_hunt.fetch_posts(first=ph_first))
    items.extend(reddit.fetch_posts(limit_per_sub=reddit_limit))
    return items
