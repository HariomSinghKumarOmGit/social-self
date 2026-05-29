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


def _extract_counts(text: str) -> Dict[str, int]:
    """Extract likes, replies/comments, reposts, and saves when available."""
    clean_text = unescape(text or "")
    likes_match = re.search(r"([\d,]+)\s+likes?", clean_text, re.IGNORECASE)
    reposts_match = re.search(r"([\d,]+)\s+(retweets?|reposts?)", clean_text, re.IGNORECASE)
    comments_match = re.search(r"([\d,]+)\s+(repl(?:y|ies)|comments?)", clean_text, re.IGNORECASE)
    saves_match = re.search(r"([\d,]+)\s+(bookmarks?|saves?)", clean_text, re.IGNORECASE)
    likes = int(likes_match.group(1).replace(",", "")) if likes_match else 0
    reposts = int(reposts_match.group(1).replace(",", "")) if reposts_match else 0
    comments = int(comments_match.group(1).replace(",", "")) if comments_match else 0
    saves = int(saves_match.group(1).replace(",", "")) if saves_match else 0
    return {"likes": likes, "comments": comments, "shares": reposts, "saves": saves}


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
                    views=0,
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
