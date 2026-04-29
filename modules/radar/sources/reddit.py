"""
Reddit: public JSON listings for startup-related subreddits (no OAuth).
Uses a descriptive User-Agent per Reddit API guidelines.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from modules.radar.company_filter import reddit_post_is_company_candidate
from modules.radar.types import TrendingStartup

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = ("startups", "SideProject", "EntrepreneurRideAlong")
REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT",
    "ai-vc-analyst-radar/0.1 by local-dev (research; contact: noreply@example.com)",
)


def _post_to_trending(
    d: dict[str, Any], subreddit: str
) -> TrendingStartup | None:
    pid = d.get("id")
    title = (d.get("title") or "").strip()
    if not pid or not title:
        return None
    selftext = (d.get("selftext") or "").strip()
    desc = selftext if len(selftext) > 40 else f"{title}. {selftext}".strip()
    if len(desc) > 8000:
        desc = desc[:8000] + "…"
    ups = int(d.get("ups") or 0)
    num_comments = int(d.get("num_comments") or 0)
    permalink = (d.get("permalink") or "").strip()
    link = (d.get("url") or "").strip()
    if permalink.startswith("/"):
        full_reddit = f"{REDDIT_BASE}{permalink}"
    else:
        full_reddit = f"{REDDIT_BASE}/r/{subreddit}/comments/{pid}/"
    # Prefer external URL for link posts; else Reddit thread
    url = link if link and "reddit.com" not in link else full_reddit
    url = url[:2048]
    external_id = f"reddit_{subreddit}_{pid}"
    domain_field = (d.get("domain") or "").strip().lower()
    if not reddit_post_is_company_candidate(title, domain_field, url):
        return None
    return TrendingStartup(
        name=title[:255],
        description=desc or title[:500],
        url=url,
        upvotes=ups,
        comments_count=num_comments,
        source="reddit",
        external_id=external_id,
        sector="",
        stage="",
    )


def fetch_posts(
    subreddits: tuple[str, ...] | None = None,
    limit_per_sub: int = 15,
    timeout: float = 20.0,
) -> list[TrendingStartup]:
    subs = subreddits or DEFAULT_SUBREDDITS
    headers = {"User-Agent": USER_AGENT}
    out: list[TrendingStartup] = []
    lim = max(1, min(limit_per_sub, 25))

    with httpx.Client(timeout=timeout, headers=headers) as client:
        for sub in subs:
            listing_url = f"{REDDIT_BASE}/r/{sub}/hot.json?limit={lim}"
            try:
                r = client.get(listing_url)
                r.raise_for_status()
                payload = r.json()
            except Exception as e:
                logger.warning("Reddit fetch failed for r/%s: %s", sub, e)
                continue
            children = ((payload.get("data") or {}).get("children")) or []
            for ch in children:
                d = (ch or {}).get("data") or {}
                if d.get("stickied"):
                    continue
                row = _post_to_trending(d, sub)
                if row:
                    out.append(row)
    return out
