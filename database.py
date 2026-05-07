# Module: database | Purpose: SQLite storage and post state transitions.
# Public API: init_db, save_post, get_pending, approve_post, reject_post, get_scheduled, mark_posted

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path("agent.db")

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_POSTED = "posted"

VALID_STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_POSTED}

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _get_connection() -> sqlite3.Connection:
    """Create and return a SQLite connection with row mapping enabled."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Initialize the database schema if it does not already exist."""
    try:
        with closing(_get_connection()) as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform TEXT NOT NULL,
                        author TEXT NOT NULL,
                        content TEXT NOT NULL,
                        media_url TEXT,
                        engagement_score REAL NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'pending',
                        scheduled_time TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        CHECK (status IN ('pending', 'approved', 'rejected', 'posted'))
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_posts_status
                    ON posts (status)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_posts_scheduled_time
                    ON posts (scheduled_time)
                    """
                )
        logger.info("Database initialized at %s", DB_PATH.resolve())
    except sqlite3.Error:
        logger.exception("Failed to initialize database.")
        raise


def save_post(
    platform: str,
    author: str,
    content: str,
    media_url: Optional[str] = None,
    engagement_score: float = 0.0,
) -> int:
    """Insert a pending post and return the newly created post ID."""
    created_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO posts (
                        platform,
                        author,
                        content,
                        media_url,
                        engagement_score,
                        status,
                        scheduled_time,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        author,
                        content,
                        media_url,
                        engagement_score,
                        STATUS_PENDING,
                        None,
                        created_at,
                        created_at,
                    ),
                )
                post_id = int(cursor.lastrowid)
        logger.info("Saved post %s from %s", post_id, platform)
        return post_id
    except sqlite3.Error:
        logger.exception("Failed to save post from %s", platform)
        raise


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Convert SQLite rows to plain dictionaries."""
    return [dict(row) for row in rows]


def get_pending() -> List[Dict[str, Any]]:
    """Return all posts with pending status ordered by creation time."""
    try:
        with closing(_get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM posts
                WHERE status = ?
                ORDER BY created_at ASC
                """,
                (STATUS_PENDING,),
            ).fetchall()
        return _rows_to_dicts(rows)
    except sqlite3.Error:
        logger.exception("Failed to fetch pending posts.")
        raise


def approve_post(post_id: int, scheduled_time: str) -> bool:
    """Mark a pending post as approved and set the scheduled time."""
    updated_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE posts
                    SET status = ?, scheduled_time = ?, updated_at = ?
                    WHERE id = ? AND status = ?
                    """,
                    (
                        STATUS_APPROVED,
                        scheduled_time,
                        updated_at,
                        post_id,
                        STATUS_PENDING,
                    ),
                )
        changed = cursor.rowcount > 0
        if changed:
            logger.info("Approved post %s for %s", post_id, scheduled_time)
        else:
            logger.warning("Post %s was not approved (missing or not pending).", post_id)
        return changed
    except sqlite3.Error:
        logger.exception("Failed to approve post %s", post_id)
        raise


def reject_post(post_id: int) -> bool:
    """Mark a pending post as rejected."""
    updated_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE posts
                    SET status = ?, updated_at = ?
                    WHERE id = ? AND status = ?
                    """,
                    (STATUS_REJECTED, updated_at, post_id, STATUS_PENDING),
                )
        changed = cursor.rowcount > 0
        if changed:
            logger.info("Rejected post %s", post_id)
        else:
            logger.warning("Post %s was not rejected (missing or not pending).", post_id)
        return changed
    except sqlite3.Error:
        logger.exception("Failed to reject post %s", post_id)
        raise


def get_scheduled() -> List[Dict[str, Any]]:
    """Return approved posts that have a scheduled time."""
    try:
        with closing(_get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM posts
                WHERE status = ? AND scheduled_time IS NOT NULL
                ORDER BY scheduled_time ASC
                """,
                (STATUS_APPROVED,),
            ).fetchall()
        return _rows_to_dicts(rows)
    except sqlite3.Error:
        logger.exception("Failed to fetch scheduled posts.")
        raise


def mark_posted(post_id: int) -> bool:
    """Mark an approved post as posted."""
    updated_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE posts
                    SET status = ?, updated_at = ?
                    WHERE id = ? AND status = ?
                    """,
                    (STATUS_POSTED, updated_at, post_id, STATUS_APPROVED),
                )
        changed = cursor.rowcount > 0
        if changed:
            logger.info("Marked post %s as posted", post_id)
        else:
            logger.warning("Post %s was not marked posted (missing or not approved).", post_id)
        return changed
    except sqlite3.Error:
        logger.exception("Failed to mark post %s as posted", post_id)
        raise


init_db()
