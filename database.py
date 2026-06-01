# Module: database | Purpose: SQLite storage and post state transitions.
# Public API: init_db, save_post, get_pending, get_post_by_id, approve_post, reject_post, get_scheduled, mark_posted, get_posts_feed,
#             get_managed_accounts, add_managed_account, delete_managed_account, set_target_account,
#             get_default_time, set_default_time, format_time_display, get_time_slots, get_preferences,
#             delete_posts_older_than_days

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import ACCOUNTS

# Always resolve DB relative to repo root (not process cwd — bot may start from telegram_bot/).
_PROJECT_ROOT = Path(__file__).resolve().parent


def _resolve_db_path() -> Path:
    """Use /tmp on Vercel/Lambda (only writable path in serverless)."""
    override = os.environ.get("DATABASE_PATH", "").strip()
    if override:
        return Path(override)
    if (
        os.environ.get("VERCEL")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    ):
        return Path("/tmp/agent.db")
    return _PROJECT_ROOT / "agent.db"


DB_PATH = _resolve_db_path()

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
                        post_url TEXT,
                        media_url TEXT,
                        likes INTEGER NOT NULL DEFAULT 0,
                        comments INTEGER NOT NULL DEFAULT 0,
                        shares INTEGER NOT NULL DEFAULT 0,
                        saves INTEGER NOT NULL DEFAULT 0,
                        views INTEGER NOT NULL DEFAULT 0,
                        engagement_score REAL NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'pending',
                        scheduled_date TEXT,
                        scheduled_time TEXT,
                        target_account TEXT,
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
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS managed_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_type TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        username TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(account_type, platform, username)
                    )
                    """
                )
                _ensure_posts_columns(conn)
                _backfill_scheduled_date(conn)
                _sync_source_accounts_from_config(conn)
        logger.info("Database initialized at %s", DB_PATH.resolve())
    except sqlite3.Error:
        logger.exception("Failed to initialize database.")
        raise


def _sync_source_accounts_from_config(conn: sqlite3.Connection) -> None:
    """Ensure configured scrape accounts exist as managed source accounts."""
    now = _utc_now_iso()
    for platform, usernames in ACCOUNTS.items():
        for username in usernames:
            if not username:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO managed_accounts (
                    account_type, platform, username, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                ("source", platform, username.strip(), now, now),
            )


def _ensure_posts_columns(conn: sqlite3.Connection) -> None:
    """Ensure new posts columns exist for backward compatibility."""
    existing_columns = {
        row[1]
        for row in conn.execute(
            """
            PRAGMA table_info(posts)
            """
        ).fetchall()
    }
    required_columns = {
        "post_url": "TEXT",
        "likes": "INTEGER NOT NULL DEFAULT 0",
        "comments": "INTEGER NOT NULL DEFAULT 0",
        "shares": "INTEGER NOT NULL DEFAULT 0",
        "saves": "INTEGER NOT NULL DEFAULT 0",
        "views": "INTEGER NOT NULL DEFAULT 0",
        "target_account": "TEXT",
        "scheduled_date": "TEXT",
    }
    for column_name, column_sql in required_columns.items():
        if column_name not in existing_columns:
            alter_statement = "ALTER TABLE posts ADD COLUMN " + column_name + " " + column_sql
            conn.execute(
                alter_statement
            )


def _backfill_scheduled_date(conn: sqlite3.Connection) -> None:
    """
    Backfill scheduled_date for older rows where only scheduled_time was stored.

    We prefer the date component of created_at when available; otherwise today (UTC).
    """
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        conn.execute(
            """
            UPDATE posts
            SET scheduled_date = COALESCE(substr(created_at, 1, 10), ?)
            WHERE status = ? AND scheduled_time IS NOT NULL AND scheduled_date IS NULL
            """,
            (today, STATUS_APPROVED),
        )
    except sqlite3.Error:
        logger.exception("Failed to backfill scheduled_date.")
        raise


# ---------------------------------------------------------------------------
# Preferences (smart default scheduling)
# ---------------------------------------------------------------------------


PREF_DEFAULT_POST_TIME = "default_post_time"


def get_preferences() -> Dict[str, str]:
    """Return all user preferences as a key/value mapping."""
    try:
        with closing(_get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT key, value FROM user_preferences
                """
            ).fetchall()
        return {str(r["key"]): str(r["value"]) for r in rows}
    except sqlite3.Error:
        logger.exception("Failed to fetch preferences.")
        raise


def get_default_time() -> str:
    """Returns stored default time, or '19:00' if not set yet."""
    try:
        with closing(_get_connection()) as conn:
            row = conn.execute(
                """
                SELECT value FROM user_preferences
                WHERE key = ?
                LIMIT 1
                """,
                (PREF_DEFAULT_POST_TIME,),
            ).fetchone()
        value = str(row["value"]) if row and row["value"] else ""
        return value if _is_hhmm(value) else "19:00"
    except sqlite3.Error:
        logger.exception("Failed to read default time preference.")
        raise


def set_default_time(time_24hr: str) -> None:
    """Saves new default time. Called every time user confirms a schedule."""
    if not _is_hhmm(time_24hr):
        raise ValueError("time_24hr must be HH:MM in 24h format")
    now = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO user_preferences (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (PREF_DEFAULT_POST_TIME, time_24hr, now),
                )
    except sqlite3.Error:
        logger.exception("Failed to set default time preference.")
        raise


def format_time_display(time_24hr: str) -> str:
    """Converts '19:00' → '7:00 PM' for display."""
    if not _is_hhmm(time_24hr):
        return time_24hr
    h, m = [int(x) for x in time_24hr.split(":")]
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d} {suffix}"


def get_time_slots() -> List[Dict[str, object]]:
    """
    Returns all available time slots from config.POST_TIMES,
    with the default time marked.
    Default slot is always first in the list.
    """
    default_time = get_default_time()
    slots = []
    seen = set()
    all_times = [default_time] + list(POST_TIMES or [])
    for t in all_times:
        if not _is_hhmm(t) or t in seen:
            continue
        seen.add(t)
        slots.append(
            {
                "time": t,
                "display": format_time_display(t),
                "is_default": t == default_time,
            }
        )
    return slots


def _is_hhmm(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 5 or value[2] != ":":
        return False
    hh, mm = value.split(":", 1)
    if not (hh.isdigit() and mm.isdigit()):
        return False
    h = int(hh)
    m = int(mm)
    return 0 <= h <= 23 and 0 <= m <= 59


def save_post(
    platform: str,
    author: str,
    content: str,
    post_url: Optional[str] = None,
    media_url: Optional[str] = None,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    views: int = 0,
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
                        post_url,
                        media_url,
                        likes,
                        comments,
                        shares,
                        saves,
                        views,
                        engagement_score,
                        status,
                        scheduled_date,
                        scheduled_time,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        author,
                        content,
                        post_url,
                        media_url,
                        likes,
                        comments,
                        shares,
                        saves,
                        views,
                        engagement_score,
                        STATUS_PENDING,
                        None,
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


def get_post_by_id(post_id: int) -> Optional[Dict[str, Any]]:
    """Return a single post dictionary by ID, or None when not found."""
    try:
        with closing(_get_connection()) as conn:
            row = conn.execute(
                """
                SELECT * FROM posts
                WHERE id = ?
                LIMIT 1
                """,
                (post_id,),
            ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        logger.exception("Failed to fetch post %s.", post_id)
        raise


def approve_post(post_id: int, scheduled_time: str) -> bool:
    """
    Mark a pending post as approved and set the scheduled time (backward compatible).

    This older API sets schedule for *today* in UTC.
    Prefer schedule_post(post_id, scheduled_date, scheduled_time).
    """
    today = datetime.now(timezone.utc).date().isoformat()
    return schedule_post(post_id=post_id, scheduled_date=today, scheduled_time=scheduled_time)


def schedule_post(post_id: int, scheduled_date: str, scheduled_time: str) -> bool:
    """Schedule a pending post by setting date+time and marking it approved."""
    if not _is_hhmm(scheduled_time):
        raise ValueError("scheduled_time must be HH:MM in 24h format")
    updated_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE posts
                    SET status = ?, scheduled_date = ?, scheduled_time = ?, updated_at = ?
                    WHERE id = ? AND status = ?
                    """,
                    (
                        STATUS_APPROVED,
                        scheduled_date,
                        scheduled_time,
                        updated_at,
                        post_id,
                        STATUS_PENDING,
                    ),
                )
        changed = cursor.rowcount > 0
        if changed:
            logger.info("Scheduled post %s for %s %s", post_id, scheduled_date, scheduled_time)
        else:
            logger.warning("Post %s was not scheduled (missing or not pending).", post_id)
        return changed
    except sqlite3.Error:
        logger.exception("Failed to schedule post %s", post_id)
        raise


def reschedule_post(post_id: int, scheduled_date: str, scheduled_time: str) -> bool:
    """Reschedule an already-approved post (or schedule a pending one) to a new date+time."""
    if not _is_hhmm(scheduled_time):
        raise ValueError("scheduled_time must be HH:MM in 24h format")
    updated_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE posts
                    SET status = ?, scheduled_date = ?, scheduled_time = ?, updated_at = ?
                    WHERE id = ? AND status IN (?, ?)
                    """,
                    (
                        STATUS_APPROVED,
                        scheduled_date,
                        scheduled_time,
                        updated_at,
                        post_id,
                        STATUS_PENDING,
                        STATUS_APPROVED,
                    ),
                )
        return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Failed to reschedule post %s", post_id)
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


def cancel_post(post_id: int) -> bool:
    """Cancel a pending/approved post by moving it to rejected state."""
    updated_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE posts
                    SET status = ?, updated_at = ?
                    WHERE id = ? AND status IN (?, ?)
                    """,
                    (STATUS_REJECTED, updated_at, post_id, STATUS_PENDING, STATUS_APPROVED),
                )
        changed = cursor.rowcount > 0
        if changed:
            logger.info("Cancelled post %s", post_id)
        else:
            logger.warning("Post %s was not cancelled (missing or already final).", post_id)
        return changed
    except sqlite3.Error:
        logger.exception("Failed to cancel post %s", post_id)
        raise


def get_scheduled() -> List[Dict[str, Any]]:
    """Return approved posts that have a scheduled time."""
    try:
        with closing(_get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM posts
                WHERE status = ? AND scheduled_date IS NOT NULL AND scheduled_time IS NOT NULL
                ORDER BY scheduled_date ASC, scheduled_time ASC
                """,
                (STATUS_APPROVED,),
            ).fetchall()
        return _rows_to_dicts(rows)
    except sqlite3.Error:
        logger.exception("Failed to fetch scheduled posts.")
        raise


def get_posts_feed() -> List[Dict[str, Any]]:
    """Return all posts for the feed UI (newest first)."""
    try:
        with closing(_get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM posts
                ORDER BY created_at DESC
                """
            ).fetchall()
        return _rows_to_dicts(rows)
    except sqlite3.Error:
        logger.exception("Failed to fetch feed posts.")
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


def set_target_account(post_id: int, target_account: str) -> bool:
    """Assign a posting account for a post."""
    updated_at = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE posts
                    SET target_account = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (target_account, updated_at, post_id),
                )
        return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Failed to set target account for post %s", post_id)
        raise


def get_managed_accounts(account_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return source or posting accounts used by dashboard and scheduler."""
    try:
        with closing(_get_connection()) as conn:
            if account_type:
                rows = conn.execute(
                    """
                    SELECT * FROM managed_accounts
                    WHERE account_type = ?
                    ORDER BY platform ASC, username ASC
                    """,
                    (account_type,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM managed_accounts
                    ORDER BY account_type ASC, platform ASC, username ASC
                    """
                ).fetchall()
        return _rows_to_dicts(rows)
    except sqlite3.Error:
        logger.exception("Failed to fetch managed accounts.")
        raise


def add_managed_account(account_type: str, platform: str, username: str) -> bool:
    """Insert a managed source/posting account if not already present."""
    now = _utc_now_iso()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO managed_accounts (
                        account_type, platform, username, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (account_type, platform, username.strip(), now, now),
                )
                result = conn.execute(
                    """
                    SELECT changes() AS changes_count
                    """
                ).fetchone()
        return bool(result and int(result[0]) > 0)
    except sqlite3.Error:
        logger.exception("Failed to add managed account.")
        raise


def delete_posts_older_than_days(days: int) -> int:
    """Delete posts older than the given number of days (by created_at). Returns rows removed."""
    if days < 1:
        raise ValueError("days must be at least 1")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    DELETE FROM posts
                    WHERE created_at < ?
                    """,
                    (cutoff,),
                )
        deleted = int(cursor.rowcount)
        if deleted:
            logger.info("Deleted %s posts older than %s days (before %s).", deleted, days, cutoff)
        return deleted
    except sqlite3.Error:
        logger.exception("Failed to delete posts older than %s days.", days)
        raise


def delete_managed_account(account_id: int) -> bool:
    """Delete managed account row by ID."""
    try:
        with closing(_get_connection()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    DELETE FROM managed_accounts
                    WHERE id = ?
                    """,
                    (account_id,),
                )
        return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Failed to delete managed account %s", account_id)
        raise


# init_db() has been removed from module level to prevent import-time locking.
