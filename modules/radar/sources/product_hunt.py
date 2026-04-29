"""
Product Hunt: GraphQL API when `PRODUCT_HUNT_TOKEN` is set; otherwise mock data.
Docs: https://api.producthunt.com/v2/docs
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from modules.radar.types import TrendingStartup
from modules.radar.sources.product_hunt_mock import MOCK_PRODUCT_HUNT_POSTS

logger = logging.getLogger(__name__)

PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"
USER_AGENT = os.environ.get(
    "PRODUCT_HUNT_USER_AGENT", "ai-vc-analyst-radar/0.1 (local dev)"
)

POSTS_QUERY = """
query TrendingPosts($first: Int!) {
  posts(first: $first, order: VOTES) {
    edges {
      node {
        id
        name
        tagline
        votesCount
        commentsCount
        url
        website
      }
    }
  }
}
"""


def _node_to_trending(node: dict[str, Any]) -> TrendingStartup | None:
    node_id = node.get("id")
    name = (node.get("name") or "").strip()
    if not node_id or not name:
        return None
    tagline = (node.get("tagline") or "").strip()
    votes = int(node.get("votesCount") or 0)
    comments = int(node.get("commentsCount") or 0)
    ph_url = (node.get("url") or "").strip()
    website = (node.get("website") or "").strip()
    url = website or ph_url or f"https://www.producthunt.com/posts/{node_id}"
    return TrendingStartup(
        name=name[:255],
        description=tagline[:8000],
        url=url[:2048],
        upvotes=votes,
        comments_count=comments,
        source="product_hunt",
        external_id=str(node_id),
        sector="",
        stage="",
    )


def fetch_posts(first: int = 15, timeout: float = 20.0) -> list[TrendingStartup]:
    token = os.environ.get("PRODUCT_HUNT_TOKEN", "").strip()
    if not token:
        logger.info("PRODUCT_HUNT_TOKEN unset — using mock Product Hunt data")
        return list(MOCK_PRODUCT_HUNT_POSTS)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    payload = {
        "query": POSTS_QUERY,
        "variables": {"first": min(first, 20)},
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(PH_GRAPHQL_URL, json=payload, headers=headers)
            r.raise_for_status()
            body = r.json()
    except Exception as e:
        logger.warning("Product Hunt API failed (%s); using mock data", e)
        return list(MOCK_PRODUCT_HUNT_POSTS)

    errors = body.get("errors")
    if errors:
        logger.warning("Product Hunt GraphQL errors: %s; using mock", errors)
        return list(MOCK_PRODUCT_HUNT_POSTS)

    data = body.get("data") or {}
    posts = (data.get("posts") or {}).get("edges") or []
    out: list[TrendingStartup] = []
    for edge in posts:
        node = (edge or {}).get("node") or {}
        row = _node_to_trending(node)
        if row:
            out.append(row)
    if not out:
        logger.warning("Product Hunt returned no posts; using mock data")
        return list(MOCK_PRODUCT_HUNT_POSTS)
    return out
