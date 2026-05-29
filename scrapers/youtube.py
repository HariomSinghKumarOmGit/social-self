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

def _resolve_channel_id(handle: str) -> Optional[str]:
    """Resolve a YouTube @handle or username to a channel ID by scraping the page."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    for url in [f"https://www.youtube.com/@{handle}", f"https://www.youtube.com/c/{handle}"]:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            # Look for channel_id in meta tags or page source
            match = re.search(r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]+)"', resp.text)
            if not match:
                match = re.search(r'channel_id=(UC[a-zA-Z0-9_-]+)', resp.text)
            if not match:
                match = re.search(r'<meta\s+itemprop="channelId"\s+content="(UC[a-zA-Z0-9_-]+)"', resp.text)
            if match:
                channel_id = match.group(1)
                logger.info("Resolved YouTube handle @%s -> %s", handle, channel_id)
                return channel_id
        except Exception:
            logger.debug("Failed resolving YouTube handle @%s via %s", handle, url)
    logger.warning("Could not resolve YouTube channel ID for: %s", handle)
    return None


def scrape_youtube() -> List[Dict[str, object]]:
    """Scrape recent YouTube entries for configured accounts and save to DB."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    saved_items: List[Dict[str, object]] = []

    for username in ACCOUNTS.get("youtube", []):
        # Try multiple RSS URL formats — modern channels use @handle
        feed = None
        feed_urls = [
            f"https://www.youtube.com/feeds/videos.xml?user={username}",
            f"https://www.youtube.com/feeds/videos.xml?channel_id={username}",
        ]
        for feed_url in feed_urls:
            feed = _fetch_feed(feed_url)
            if feed and feed.entries:
                break

        # If RSS failed, try resolving @handle to channel ID
        if not feed or not getattr(feed, "entries", []):
            channel_id = _resolve_channel_id(username)
            if channel_id:
                feed = _fetch_feed(
                    f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                )

        if not feed or not getattr(feed, "entries", []):
            logger.warning("YouTube: no feed entries found for %s", username)
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
