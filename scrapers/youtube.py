# Module: youtube_scraper | Purpose: Fetch recent YouTube posts via RSS.
# Public API: scrape_youtube

from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

import feedparser
import requests

from config import ACCOUNTS, LOOKBACK_DAYS
from database import save_post

logger = logging.getLogger(__name__)


def _extract_view_count(entry: feedparser.FeedParserDict) -> int:
    """Extract approximate view count from RSS entry fields when possible."""
    media_stats = entry.get("media_statistics", {})
    if isinstance(media_stats, dict) and media_stats.get("views"):
        try:
            return int(media_stats["views"])
        except (TypeError, ValueError):
            pass

    summary_text = f"{entry.get('summary', '')} {entry.get('title', '')}"
    match = re.search(r"([\d,]+)\s+views", summary_text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            return 0
    return 0


def _entry_is_recent(entry: feedparser.FeedParserDict, cutoff: datetime) -> bool:
    """Check whether a feed entry is newer than the provided cutoff."""
    published = entry.get("published")
    if not published:
        return False
    try:
        published_dt = parsedate_to_datetime(published)
        if published_dt.tzinfo is None:
            published_dt = published_dt.replace(tzinfo=timezone.utc)
        return published_dt >= cutoff
    except (TypeError, ValueError):
        return False


def _fetch_feed(url: str, retries: int = 3) -> Optional[feedparser.FeedParserDict]:
    """Fetch and parse a feed with retries and basic rate-limiting."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return feedparser.parse(response.text)
            logger.warning("YouTube feed status %s for %s", response.status_code, url)
        except requests.RequestException:
            logger.exception("YouTube feed fetch failed on attempt %s for %s", attempt, url)
        if attempt < retries:
            backoff = 2 ** (attempt - 1)
            time.sleep(backoff + random.uniform(0.2, 0.8))
    return None


def scrape_youtube() -> List[Dict[str, object]]:
    """Scrape recent YouTube entries for configured accounts and save to DB."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    saved_items: List[Dict[str, object]] = []

    for username in ACCOUNTS.get("youtube", []):
        feed_url = f"https://www.youtube.com/feeds/videos.xml?user={username}"
        feed = _fetch_feed(feed_url)
        if not feed:
            continue

        for entry in feed.entries:
            try:
                if not _entry_is_recent(entry, cutoff):
                    continue
                title = entry.get("title", "").strip() or "Untitled video"
                link = entry.get("link", "").strip()
                media_url = ""
                if entry.get("media_thumbnail"):
                    media_url = entry["media_thumbnail"][0].get("url", "")
                views = _extract_view_count(entry)
                content = f"{title}\n{link}".strip()
                post_id = save_post(
                    platform="youtube",
                    author=username,
                    content=content,
                    post_url=link or None,
                    media_url=media_url or None,
                    likes=0,
                    comments=0,
                    shares=0,
                    views=views,
                    engagement_score=float(views),
                )
                saved_items.append(
                    {
                        "id": post_id,
                        "platform": "youtube",
                        "author": username,
                        "content": title,
                        "post_url": link,
                        "media_url": media_url,
                        "view_count": views,
                    }
                )
            except Exception:
                logger.exception("Failed processing YouTube entry for %s", username)
        time.sleep(random.uniform(1.0, 1.8))

    logger.info("YouTube scrape completed. Saved %s items.", len(saved_items))
    return saved_items
