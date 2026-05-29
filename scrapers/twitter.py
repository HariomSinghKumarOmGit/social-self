# Module: twitter_scraper | Purpose: Fetch recent tweets through Nitter RSS.
# Public API: scrape_twitter

from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Dict, List, Optional

import feedparser
import requests

from config import ACCOUNTS, LOOKBACK_DAYS
from database import save_post

logger = logging.getLogger(__name__)

NITTER_HOSTS = (
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.woodland.cafe",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
)


def _parse_count(raw: str) -> int:
    """Parse '1,234' or '12.5K' style counts from Nitter/RSS text."""
    if not raw:
        return 0
    s = raw.strip().replace(",", "").upper()
    try:
        if s.endswith("K"):
            return int(float(s[:-1]) * 1_000)
        if s.endswith("M"):
            return int(float(s[:-1]) * 1_000_000)
        if s.endswith("B"):
            return int(float(s[:-1]) * 1_000_000_000)
        return int(float(s))
    except ValueError:
        return 0


def _extract_counts(text: str) -> Dict[str, int]:
    """Extract likes, replies/comments, reposts, saves, and views when available."""
    clean_text = unescape(text or "")
    patterns = [
        (r"([\d,.]+[KMB]?)\s+likes?", "likes"),
        (r"([\d,.]+[KMB]?)\s+(retweets?|reposts?)", "shares"),
        (r"([\d,.]+[KMB]?)\s+(repl(?:y|ies)|comments?)", "comments"),
        (r"([\d,.]+[KMB]?)\s+(bookmarks?|saves?)", "saves"),
        (r"([\d,.]+[KMB]?)\s+views?", "views"),
    ]
    out = {"likes": 0, "comments": 0, "shares": 0, "saves": 0, "views": 0}
    for pattern, key in patterns:
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            out[key] = _parse_count(match.group(1))
    return out


def _fetch_feed(url: str, retries: int = 3) -> Optional[feedparser.FeedParserDict]:
    """Fetch RSS feed text and parse it with retries."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return feedparser.parse(response.text)
            logger.warning("Nitter status %s for %s", response.status_code, url)
        except requests.RequestException:
            logger.exception("Nitter fetch failed attempt %s for %s", attempt, url)
        if attempt < retries:
            backoff = 2 ** (attempt - 1)
            time.sleep(backoff + random.uniform(0.2, 1.0))
    return None


def _entry_is_recent(entry: feedparser.FeedParserDict, cutoff: datetime) -> bool:
    """Return True when the entry was published after cutoff."""
    try:
        published = parsedate_to_datetime(entry.get("published", ""))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return published >= cutoff
    except (TypeError, ValueError):
        return False


def scrape_twitter() -> List[Dict[str, object]]:
    """Scrape recent tweets from Nitter RSS and persist them."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    saved_items: List[Dict[str, object]] = []

    for username in ACCOUNTS.get("twitter", []):
        feed = None
        for host in NITTER_HOSTS:
            feed = _fetch_feed(f"{host}/{username}/rss")
            if feed:
                break

        if not feed:
            logger.error("All Nitter hosts failed for %s", username)
            continue

        for entry in feed.entries:
            try:
                if not _entry_is_recent(entry, cutoff):
                    continue
                summary = entry.get("summary", "")
                title = unescape(entry.get("title", "")).strip()
                counts = _extract_counts(f"{summary} {title}")
                engagement = (
                    counts["likes"]
                    + counts["comments"] * 3
                    + counts["shares"] * 2
                    + counts["views"] * 0.01
                )
                post_url = entry.get("link", "").strip()
                media_url = ""
                if entry.get("media_content"):
                    media_url = entry["media_content"][0].get("url", "")

                post_id = save_post(
                    platform="twitter",
                    author=username,
                    content=title or post_url,
                    post_url=post_url or None,
                    media_url=media_url or None,
                    likes=counts["likes"],
                    comments=counts["comments"],
                    shares=counts["shares"],
                    saves=counts["saves"],
                    views=counts["views"],
                    engagement_score=float(engagement),
                )
                saved_items.append(
                    {
                        "id": post_id,
                        "platform": "twitter",
                        "author": username,
                        "content": title,
                        "post_url": post_url,
                        "media_url": media_url,
                        "likes": counts["likes"],
                        "comments": counts["comments"],
                        "retweets": counts["shares"],
                        "saves": counts["saves"],
                    }
                )
            except Exception:
                logger.exception("Failed processing Twitter entry for %s", username)
        time.sleep(random.uniform(1.0, 1.8))

    logger.info("Twitter scrape completed. Saved %s items.", len(saved_items))
    return saved_items
