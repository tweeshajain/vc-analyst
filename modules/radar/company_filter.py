"""
Filter radar pipeline to company / product listings vs discussion threads and articles.

Reddit posts often link to Medium, Substack, or news sites — those are excluded.
Product Hunt and manual rows always pass.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

_STRICT = os.environ.get("RADAR_STRICT_COMPANIES", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)

# Outbound link hosts that are usually editorial / newsletters, not a company site.
_PUBLISHING_HOST_SUFFIXES: tuple[str, ...] = (
    "medium.com",
    "substack.com",
    "substackcdn.com",
    "ghost.io",
    "beehiiv.com",
    "mailchi.mp",
    "nytimes.com",
    "wsj.com",
    "washingtonpost.com",
    "theatlantic.com",
    "theguardian.com",
    "bbc.co.uk",
    "bbc.com",
    "cnn.com",
    "forbes.com",
    "bloomberg.com",
    "reuters.com",
    "economist.com",
    "axios.com",
    "theverge.com",
    "wired.com",
    "techcrunch.com",
    "arstechnica.com",
    "theinformation.com",
    "venturebeat.com",
)

# Titles that are clearly subreddit meta / discussion, not a company pitch.
_TITLE_BAD_PREFIXES: tuple[str, ...] = (
    "discussion:",
    "[discussion]",
    "weekly ",
    "monthly ",
    "daily thread",
    "megathread",
    "meta:",
    "community ",
    "announcement:",
    "readme:",
    "rant:",
    "success story sunday",
    "failure friday",
    "free talk ",
    "check-in ",
    "morning thread",
    "evening thread",
)

_TITLE_META_RE = re.compile(
    r"^\s*(\[[^\]]*\]\s*)?"
    r"(discussion|weekly\s+\w+|monthly\s+\w+|megathread|community\s+guidelines)\b",
    re.I,
)


def _normalize_host(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    try:
        h = urlparse(raw).netloc.lower().removeprefix("www.")
    except Exception:
        return ""
    return h


def _host_is_publishing(url_host: str) -> bool:
    h = (url_host or "").lower().removeprefix("www.")
    if not h:
        return False
    for suf in _PUBLISHING_HOST_SUFFIXES:
        if h == suf or h.endswith("." + suf):
            return True
    return False


def _host_is_reddit(url_host: str) -> bool:
    h = (url_host or "").lower()
    return any(x in h for x in _REDDIT_HOST_FRAGMENTS)


def reddit_post_is_company_candidate(title: str, domain_or_host: str, url: str) -> bool:
    """
    Heuristic for Reddit JSON `domain` field or resolved URL host.
    Drop obvious discussion threads, weekly posts, and links to publishing domains.
    """
    if not _STRICT:
        return True

    t = (title or "").strip()
    tl = t.lower()

    if not t or len(t) < 3:
        return False

    for p in _TITLE_BAD_PREFIXES:
        if tl.startswith(p):
            return False

    if _TITLE_META_RE.match(t):
        return False

    host = (domain_or_host or "").lower().strip().removeprefix("www.")
    if host.startswith("self."):
        host = ""  # self-post: judge by title only (already passed)

    url_host = _normalize_host(url) or host

    if url_host and _host_is_publishing(url_host):
        return False

    # Link goes to an editorial domain while Reddit also sent a domain field
    if host and not host.startswith("self.") and _host_is_publishing(host):
        return False

    return True


def startup_is_company_candidate(source: str, name: str, url: str | None) -> bool:
    """Apply company filter to persisted Startup rows (by source)."""
    if not _STRICT:
        return True

    src = (source or "").strip().lower()
    if src in ("product_hunt", "manual", "demo", "seed"):
        return True
    if src != "reddit":
        return True

    url_host = _normalize_host(url or "")
    return reddit_post_is_company_candidate(name or "", url_host, url or "")
