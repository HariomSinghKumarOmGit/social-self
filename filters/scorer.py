# Module: scorer | Purpose: Normalize engagement into a 0-100 score.
# Public API: calculate_score, score_pending_posts

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Dict, List

from database import DB_PATH, get_pending

logger = logging.getLogger(__name__)


def calculate_score(likes: int, comments: int, shares: int, views: int = 0) -> float:
    """Calculate a bounded engagement score in the 0-100 range."""
    weighted = (likes * 1) + (comments * 3) + (shares * 2) + (views * 0.01)
    return round(min(100.0, weighted / 100.0), 2)


def _update_post_score(post_id: int, score: float) -> None:
    """Persist score for a post in SQLite."""
    updated_at = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute(
                """
                UPDATE posts
                SET engagement_score = ?, updated_at = ?
                WHERE id = ?
                """,
                (score, updated_at, post_id),
            )


def score_pending_posts() -> int:
    """
    Score all pending posts.

    Uses granular engagement fields if available.
    """
    updated = 0
    try:
        pending_posts: List[Dict[str, object]] = get_pending()
        for post in pending_posts:
            score = calculate_score(
                likes=int(post.get("likes", 0) or 0),
                comments=int(post.get("comments", 0) or 0),
                shares=int(post.get("shares", 0) or 0),
                views=int(post.get("views", 0) or 0),
            )
            _update_post_score(int(post["id"]), score)
            updated += 1
    except Exception:
        logger.exception("Failed while scoring pending posts.")
        return updated

    logger.info("Scoring completed. Updated %s pending posts.", updated)
    return updated
