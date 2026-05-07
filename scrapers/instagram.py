# Module: instagram_scraper | Purpose: Fetch recent Instagram posts via Apify.
# Public API: scrape_instagram

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from apify_client import ApifyClient

from config import ACCOUNTS, APIFY_API_TOKEN, LOOKBACK_DAYS
from database import save_post

logger = logging.getLogger(__name__)


def _safe_int(value: object) -> int:
    """Convert unknown numeric-like values into int safely."""
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _parse_iso_datetime(value: str) -> datetime:
    """Parse known ISO-like datetime strings and return UTC-aware datetime."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def scrape_instagram() -> List[Dict[str, object]]:
    """Scrape recent Instagram posts using Apify and save them to SQLite."""
    if not APIFY_API_TOKEN:
        logger.error("APIFY_API_TOKEN is missing; skipping Instagram scrape.")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    saved_items: List[Dict[str, object]] = []
    client = ApifyClient(APIFY_API_TOKEN)

    for username in ACCOUNTS.get("instagram", []):
        try:
            run_input = {
                "directUrls": [f"https://www.instagram.com/{username}/"],
                "resultsType": "posts",
                "resultsLimit": 12,
                "searchType": "user",
            }
            run = client.actor("apify/instagram-scraper").call(run_input=run_input)
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                logger.warning("No dataset returned for Instagram user %s", username)
                continue

            for item in client.dataset(dataset_id).iterate_items():
                try:
                    posted_at_raw = item.get("timestamp") or item.get("takenAt")
                    if not posted_at_raw:
                        continue
                    posted_at = _parse_iso_datetime(str(posted_at_raw))
                    if posted_at < cutoff:
                        continue

                    caption = (item.get("caption") or "").strip() or "Instagram post"
                    image_url = item.get("displayUrl") or item.get("imageUrl") or ""
                    likes = _safe_int(item.get("likesCount"))
                    comments = _safe_int(item.get("commentsCount"))
                    shares = _safe_int(item.get("sharesCount") or item.get("repostsCount"))
                    saves = _safe_int(item.get("savesCount") or item.get("savedCount"))
                    engagement = likes + comments + shares

                    post_id = save_post(
                        platform="instagram",
                        author=username,
                        content=caption,
                        post_url=item.get("url") or None,
                        media_url=image_url or None,
                        likes=likes,
                        comments=comments,
                        shares=shares,
                        saves=saves,
                        views=0,
                        engagement_score=float(engagement),
                    )
                    saved_items.append(
                        {
                            "id": post_id,
                            "platform": "instagram",
                            "author": username,
                            "content": caption,
                            "media_url": image_url,
                            "likes": likes,
                            "comments": comments,
                            "shares": shares,
                            "saves": saves,
                        }
                    )
                except Exception:
                    logger.exception("Failed processing Instagram item for %s", username)
        except Exception:
            logger.exception("Instagram scrape failed for %s", username)
        time.sleep(random.uniform(1.0, 2.0))

    logger.info("Instagram scrape completed. Saved %s items.", len(saved_items))
    return saved_items
