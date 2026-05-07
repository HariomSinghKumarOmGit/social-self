# Module: scheduler | Purpose: Periodic job runner for scraping, scoring, and posting.
# Public API: start_scheduler, run_scrape_cycle, run_post_cycle

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, List

import schedule

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from database import get_scheduled, mark_posted
from filters.scorer import score_pending_posts
from scrapers.instagram import scrape_instagram
from scrapers.twitter import scrape_twitter
from scrapers.youtube import scrape_youtube

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scraping + scoring + Telegram notification cycle
# ---------------------------------------------------------------------------


def _notify_telegram(message: str) -> None:
    """Send a plain-text notification to Telegram (best-effort)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing; skipping notification.")
        return
    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=15)
    except Exception:
        logger.exception("Failed to send Telegram notification.")


def run_scrape_cycle() -> None:
    """Execute all scrapers, score new posts, and notify via Telegram."""
    logger.info("=== Scrape cycle starting ===")
    total_saved = 0
    try:
        ig = scrape_instagram()
        total_saved += len(ig)
    except Exception:
        logger.exception("Instagram scraper crashed.")
    try:
        tw = scrape_twitter()
        total_saved += len(tw)
    except Exception:
        logger.exception("Twitter scraper crashed.")
    try:
        yt = scrape_youtube()
        total_saved += len(yt)
    except Exception:
        logger.exception("YouTube scraper crashed.")

    scored = score_pending_posts()
    logger.info("Scrape cycle done: %s new posts, %s scored.", total_saved, scored)

    _notify_telegram(
        f"🔄 Scrape cycle complete\n"
        f"New posts: {total_saved}\n"
        f"Scored: {scored}\n"
        f"Use /pending to review."
    )


# ---------------------------------------------------------------------------
# Posting cycle — triggers browser poster for due posts
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run a coroutine in a fresh event loop (safe from any thread)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _post_single(post: dict) -> bool:
    """Dispatch one approved post to the correct browser poster."""
    platform = str(post.get("platform", "")).lower()
    content = str(post.get("content", ""))
    media_url = str(post.get("media_url") or "")
    post_id = int(post["id"])

    try:
        if platform == "instagram":
            from poster.instagram_post import post_to_instagram

            if not media_url:
                logger.warning("Instagram post #%s has no media; skipping.", post_id)
                return False
            result = _run_async(post_to_instagram(media_url, content))
        elif platform == "twitter":
            from poster.twitter_post import post_to_twitter

            result = _run_async(post_to_twitter(content, media_url or None))
        elif platform == "youtube":
            from poster.youtube_post import post_to_youtube

            if not media_url:
                logger.warning("YouTube post #%s has no video; skipping.", post_id)
                return False
            title = content.split("\n")[0][:100]
            desc = content
            result = _run_async(post_to_youtube(media_url, title, desc))
        else:
            logger.warning("Unknown platform '%s' for post #%s", platform, post_id)
            return False

        success = result.get("success") == "True"
        if success:
            mark_posted(post_id)
            logger.info("✅ Posted #%s to %s", post_id, platform)
            _notify_telegram(f"✅ Posted #{post_id} to {platform.title()}")
        else:
            logger.error("❌ Post #%s failed: %s", post_id, result.get("error"))
            _notify_telegram(f"❌ Post #{post_id} failed on {platform.title()}: {result.get('error', 'unknown')}")
        return success
    except Exception:
        logger.exception("Posting crashed for #%s", post_id)
        return False


def run_post_cycle() -> None:
    """Check for approved posts due NOW and trigger browser posting."""
    logger.info("=== Post cycle starting ===")
    now = datetime.now(timezone.utc)
    current_hhmm = now.strftime("%H:%M")

    scheduled = get_scheduled()
    due_posts = [p for p in scheduled if str(p.get("scheduled_time", "")) <= current_hhmm]

    if not due_posts:
        logger.info("No due posts at %s.", current_hhmm)
        return

    logger.info("Found %s due post(s) at %s.", len(due_posts), current_hhmm)
    posted = 0
    for post in due_posts:
        if _post_single(post):
            posted += 1
    logger.info("Post cycle done: %s/%s succeeded.", posted, len(due_posts))


# ---------------------------------------------------------------------------
# Scheduler runner (blocking)
# ---------------------------------------------------------------------------


def start_scheduler() -> None:
    """Configure scheduled jobs and run the blocking polling loop."""
    schedule.every().day.at("08:00").do(run_scrape_cycle)
    schedule.every().hour.do(run_post_cycle)

    logger.info(
        "Scheduler started. Scrape at 08:00 daily, post check every hour. "
        "Next run: %s",
        schedule.next_run(),
    )

    while True:
        schedule.run_pending()
        time.sleep(30)


def start_scheduler_thread() -> threading.Thread:
    """Spawn the scheduler in a background daemon thread."""
    thread = threading.Thread(target=start_scheduler, name="scheduler", daemon=True)
    thread.start()
    return thread
