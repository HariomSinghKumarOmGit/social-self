# Module: telegram_handlers | Purpose: Callback and command handlers for moderation flow.
# Public API: register_handlers

from __future__ import annotations

import logging
import os
import threading
from typing import Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.helpers import escape_markdown

from config import ACCOUNTS, EC2_PUBLIC_IP, POST_TIMES
from database import (
    cancel_post,
    format_time_display,
    get_default_time,
    get_pending,
    get_post_by_id,
    get_scheduled,
    reject_post,
    reschedule_post,
    schedule_post,
    set_default_time,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 3
SCHEDULE_DATE_KEY = "schedule_date_by_post_id"
PENDING_PREFS_KEY = "pending_prefs"

SORT_NEWEST = "newest"
SORT_TOP_SCORE = "top"
SORT_MOST_LIKES = "likes"
DEFAULT_SORT = SORT_NEWEST

PLATFORM_ICONS = {
    "instagram": "📸",
    "twitter": "🐦",
    "youtube": "📺",
}


def _truncate_content(text: str, limit: int = 200) -> str:
    """Return a short content preview for Telegram messages."""
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else f"{cleaned[: limit - 3]}..."


def _md(text: str) -> str:
    return escape_markdown(text or "", version=2)


def _build_post_text(post: Dict[str, object]) -> str:
    """Format one post preview for Telegram."""
    platform = str(post.get("platform", "")).lower()
    icon = PLATFORM_ICONS.get(platform, "📝")
    author = str(post.get("author", "unknown"))
    score = float(post.get("engagement_score", 0.0) or 0.0)
    likes = int(post.get("likes", 0) or 0)
    comments = int(post.get("comments", 0) or 0)
    shares = int(post.get("shares", 0) or 0)
    saves = int(post.get("saves", 0) or 0)
    preview = _truncate_content(str(post.get("content", "")))
    return "\n".join(
        [
            f"{icon} *{_md(author)}*",
            f"📊 Score: {_md(f'{score:.1f}')}/100 \\| 👍 {_md(str(likes))} \\| 💬 {_md(str(comments))}",
            "",
            _md(preview),
        ]
    )


def _build_action_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Build approve/reject buttons for a single post."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{post_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{post_id}"),
            ]
        ]
    )


def _build_schedule_keyboard(post_id: int, date_iso: str) -> InlineKeyboardMarkup:
    """Build time slot buttons for the given date."""
    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []
    for time_slot in POST_TIMES:
        if not time_slot:
            continue
        label = format_time_display(time_slot)
        current_row.append(
            InlineKeyboardButton(label, callback_data=f"schedule|{post_id}|{time_slot}|{date_iso}")
        )
        if len(current_row) == 3:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(rows)


def _build_default_time_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Build default time confirmation keyboard shown right after Approve."""
    default_time = get_default_time()
    label = f"✅ Use {format_time_display(default_time)}"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(label, callback_data=f"use_default_time|{post_id}")],
            [InlineKeyboardButton("🕐 Change time", callback_data=f"change_time|{post_id}")],
            [InlineKeyboardButton("📆 Change date", callback_data=f"change_date|{post_id}")],
        ]
    )


def _today_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).date().isoformat()


def _tomorrow_iso() -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()


def _get_selected_date(context: ContextTypes.DEFAULT_TYPE, post_id: int) -> str:
    store = context.user_data.setdefault(SCHEDULE_DATE_KEY, {})
    return str(store.get(str(post_id)) or _tomorrow_iso())


def _set_selected_date(context: ContextTypes.DEFAULT_TYPE, post_id: int, date_iso: str) -> None:
    store = context.user_data.setdefault(SCHEDULE_DATE_KEY, {})
    store[str(post_id)] = date_iso


def _parse_callback(data: str) -> List[str]:
    if "|" in data:
        return data.split("|")
    return data.split(":")


def _platform_label(platform: str) -> str:
    return {
        "instagram": "📸 Insta",
        "twitter": "🐦 Twitter",
        "youtube": "📺 YouTube",
        "other": "🧩 Other",
        "": "All",
    }.get(platform, "All")


def _build_platform_keyboard(active_platform: str, offset: int) -> InlineKeyboardMarkup:
    def mk(platform: str) -> InlineKeyboardButton:
        prefix = "• " if platform == active_platform else ""
        return InlineKeyboardButton(
            f"{prefix}{_platform_label(platform)}",
            callback_data=f"pending_filter|{platform}|{offset}",
        )

    return InlineKeyboardMarkup(
        [
            [mk(""), mk("instagram")],
            [mk("twitter"), mk("youtube"), mk("other")],
        ]
    )


def _build_author_keyboard(platform: str) -> InlineKeyboardMarkup:
    """Show source account buttons for a platform (e.g. X handles)."""
    authors = ACCOUNTS.get(platform, [])
    rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton("All accounts", callback_data=f"pending_author|{platform}|")]
    ]
    row: List[InlineKeyboardButton] = []
    for author in authors:
        label = f"@{author}" if len(author) <= 18 else f"@{author[:15]}…"
        row.append(InlineKeyboardButton(label, callback_data=f"pending_author|{platform}|{author}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="pending_menu|")])
    return InlineKeyboardMarkup(rows)


def _sort_label(sort_key: str) -> str:
    return {
        SORT_NEWEST: "🕒 Newest",
        SORT_TOP_SCORE: "📈 Top score",
        SORT_MOST_LIKES: "👍 Most likes",
    }.get(sort_key, "🕒 Newest")


def _build_pending_controls_keyboard(active_platform: str, active_sort: str, offset: int) -> InlineKeyboardMarkup:
    platform_keyboard = _build_platform_keyboard(active_platform, offset).inline_keyboard

    def mk_sort(sort_key: str) -> InlineKeyboardButton:
        prefix = "• " if sort_key == active_sort else ""
        return InlineKeyboardButton(
            f"{prefix}{_sort_label(sort_key)}",
            callback_data=f"pending_sort|{sort_key}",
        )

    sort_row = [mk_sort(SORT_NEWEST), mk_sort(SORT_TOP_SCORE), mk_sort(SORT_MOST_LIKES)]
    return InlineKeyboardMarkup(platform_keyboard + [sort_row])


def _build_date_keyboard(post_id: int) -> InlineKeyboardMarkup:
    from datetime import datetime, timedelta, timezone

    base = datetime.now(timezone.utc).date()
    days = [base + timedelta(days=i) for i in range(0, 7)]
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for d in days:
        row.append(
            InlineKeyboardButton(d.strftime("%a %d %b"), callback_data=f"select_date|{post_id}|{d.isoformat()}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅ Back to time", callback_data=f"change_time|{post_id}")])
    return InlineKeyboardMarkup(rows)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome/instructions for the moderation bot."""
    del context
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "Welcome to Social Agent.\n\n"
        "Use:\n"
        "/pending - review pending posts\n"
        "/help - show commands"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help text."""
    del context
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "/start - show instructions\n"
        "/pending - review pending posts\n"
        "/insta - pending Instagram posts\n"
        "/twitter - pending Twitter posts\n"
        "/youtube - pending YouTube posts\n"
        "/other - pending other platforms\n"
        "/all - pending posts from all platforms\n"
        "/scrape - manually trigger scraping now\n"
        "/filter <text> - set your persistent pending filter\n"
        "/clearfilter - clear your persistent pending filter\n"
        "/schedule - show upcoming queue\n"
        "/scheduled - show approved queue\n"
        "/list [page] - paginated scheduled posts\n"
        "/preview <post_id> - preview one post\n"
        "/cancel <post_id> - cancel one post\n"
        "/status - queue health summary\n"
        "/settime - set your default posting time\n"
        "/stop - stop the bot process\n"
        "/help - show command list"
    )


async def scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger a scrape cycle from Telegram."""
    del context
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "🔄 Starting scrape cycle... This may take a few minutes.\n"
        "I'll notify you when it's done."
    )

    def _run_scrape():
        try:
            from scheduler import run_scrape_cycle
            run_scrape_cycle()
        except Exception:
            logger.exception("Manual scrape cycle failed.")

    thread = threading.Thread(target=_run_scrape, name="manual-scrape", daemon=True)
    thread.start()


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force-stop the bot process immediately."""
    if update.effective_message:
        await update.effective_message.reply_text("🛑 Force-stopping bot process now.")
    # Hard stop for stuck polling/session conflicts.
    os._exit(0)


async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show platform/sort options first; posts load after you pick a source."""
    if not update.effective_message:
        return
    try:
        query_text = " ".join(context.args).strip().lower()
        if not query_text:
            existing = _get_pending_prefs(context)
            query_text = existing["query"]
        context.user_data[PENDING_PREFS_KEY] = {
            "platform": "",
            "author": "",
            "sort": DEFAULT_SORT,
            "query": query_text,
        }
        subtitle = f"\nFilter: {query_text}" if query_text else ""
        await update.effective_message.reply_text(
            f"Choose platform and sort:{subtitle}",
            reply_markup=_build_pending_controls_keyboard("", DEFAULT_SORT, 0),
        )
    except Exception:
        logger.exception("pending_command failed")
        await update.effective_message.reply_text("⚠️ Could not open pending menu. Try again.")


async def _open_platform_pending(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    platform: str,
    title: str,
) -> None:
    """Open pending feed for a platform; Twitter/Insta show account picker first."""
    if not update.effective_message:
        return
    try:
        prefs = _set_pending_prefs(context, platform=platform, author="")
        if platform in {"twitter", "instagram"} and ACCOUNTS.get(platform):
            await update.effective_message.reply_text(
                f"{title}\nPick an account:",
                reply_markup=_build_author_keyboard(platform),
            )
            return
        await _send_filtered_pending_page(update.effective_message, prefs, offset=0, header=title)
    except Exception:
        logger.exception("_open_platform_pending failed for platform=%s", platform)
        await update.effective_message.reply_text("⚠️ Could not load pending posts. Try /pending again.")


async def insta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_platform_pending(update, context, "instagram", "📸 Instagram pending posts")


async def twitter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_platform_pending(update, context, "twitter", "🐦 Twitter pending posts")


async def youtube_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_platform_pending(update, context, "youtube", "📺 YouTube pending posts")


async def other_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_platform_pending(update, context, "other", "🧩 Other platform pending posts")


async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _open_platform_pending(update, context, "", "🗂 All pending posts")


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Persist user keyword filter for pending feed."""
    if not update.effective_message:
        return
    query_text = " ".join(context.args).strip().lower()
    if not query_text:
        await update.effective_message.reply_text("Usage: /filter <text>")
        return
    prefs = _set_pending_prefs(context, query_text=query_text)
    await update.effective_message.reply_text(
        f"✅ Filter saved: {prefs['query']}\nUse /pending, /insta, /twitter, /youtube, /other, or /all."
    )


async def clearfilter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear user keyword filter for pending feed."""
    if not update.effective_message:
        return
    prefs = _set_pending_prefs(context, query_text="")
    await update.effective_message.reply_text(
        "✅ Filter cleared.\nUse /pending or any platform command to view all matching posts."
    )


async def scheduled_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show approved posts that already have a selected schedule time."""
    del context
    if not update.effective_message:
        return

    today = _today_iso()
    posts = [p for p in get_scheduled() if str(p.get("scheduled_date") or "") == today]
    if not posts:
        await update.effective_message.reply_text("No approved scheduled posts for today.")
        return

    lines = [f"Today's queue ({today}):"]
    for post in posts:
        post_id = int(post.get("id", 0) or 0)
        platform = str(post.get("platform", "")).title()
        author = str(post.get("author", "unknown"))
        date_s = str(post.get("scheduled_date") or "")
        time_s = str(post.get("scheduled_time") or "")
        when = f"{date_s} {time_s}".strip() or "unscheduled"
        lines.append(f"#{post_id} | {platform} | @{author} | {when}")
    await update.effective_message.reply_text("\n".join(lines[:80]))


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias for /scheduled."""
    await scheduled_command(update, context)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Paginated list of scheduled posts."""
    if not update.effective_message:
        return
    page = 1
    if context.args:
        try:
            page = max(1, int(context.args[0]))
        except ValueError:
            await update.effective_message.reply_text("Usage: /list [page_number]")
            return
    per_page = 10
    posts = get_scheduled()
    if not posts:
        await update.effective_message.reply_text("No scheduled posts found.")
        return

    total = len(posts)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    chunk = posts[start : start + per_page]

    lines = [f"Scheduled posts (page {page}/{total_pages}):"]
    for post in chunk:
        post_id = int(post.get("id", 0) or 0)
        platform = str(post.get("platform", "")).title()
        author = str(post.get("author", "unknown"))
        date_s = str(post.get("scheduled_date") or "")
        time_s = str(post.get("scheduled_time") or "")
        lines.append(f"#{post_id} | {platform} | @{author} | {date_s} {time_s}".strip())
    await update.effective_message.reply_text("\n".join(lines))


async def preview_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show complete details for one post."""
    if not update.effective_message:
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /preview <post_id>")
        return
    try:
        post_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("post_id must be a number.")
        return

    post = get_post_by_id(post_id)
    if not post:
        await update.effective_message.reply_text(f"Post #{post_id} not found.")
        return

    text = "\n".join(
        [
            f"Post #{post_id}",
            f"Platform: {str(post.get('platform', '')).title()}",
            f"Author: @{str(post.get('author', 'unknown'))}",
            f"Status: {str(post.get('status', 'unknown'))}",
            f"Scheduled: {str(post.get('scheduled_date') or '-')} {str(post.get('scheduled_time') or '-')}",
            "",
            str(post.get("content", "")),
        ]
    )
    await update.effective_message.reply_text(text[:4000])


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel a post from queue."""
    if not update.effective_message:
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /cancel <post_id>")
        return
    try:
        post_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("post_id must be a number.")
        return

    if cancel_post(post_id):
        await update.effective_message.reply_text(f"✅ Cancelled post #{post_id}.")
    else:
        await update.effective_message.reply_text(f"Could not cancel post #{post_id}.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send high-level moderation/scheduling status."""
    del context
    if not update.effective_message:
        return

    pending_count = len(get_pending())
    scheduled_count = len(get_scheduled())
    await update.effective_message.reply_text(
        "System status:\n"
        f"Pending posts: {pending_count}\n"
        f"Approved scheduled: {scheduled_count}\n"
        f"Default time: {format_time_display(get_default_time())}\n"
        f"Configured time slots: {', '.join(POST_TIMES)}"
    )


async def settime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually set default posting time."""
    del context
    if not update.effective_message:
        return
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(format_time_display(t), callback_data=f"set_default|{t}")] for t in POST_TIMES]
    )
    await update.effective_message.reply_text("Pick your default posting time:", reply_markup=keyboard)


def _calendar_link() -> str:
    # Prefer explicit runtime port when provided, fallback to 5000.
    web_port = os.getenv("WEB_UI_PORT") or os.getenv("PORT") or "5000"
    if EC2_PUBLIC_IP:
        return f"http://{EC2_PUBLIC_IP}:{web_port}"
    return f"http://localhost:{web_port}"


def _get_pending_prefs(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, str]:
    prefs = context.user_data.setdefault(PENDING_PREFS_KEY, {})
    platform = str(prefs.get("platform") or "")
    author = str(prefs.get("author") or "")
    sort_key = str(prefs.get("sort") or DEFAULT_SORT)
    query_text = str(prefs.get("query") or "").strip().lower()
    if sort_key not in {SORT_NEWEST, SORT_TOP_SCORE, SORT_MOST_LIKES}:
        sort_key = DEFAULT_SORT
    return {"platform": platform, "author": author, "sort": sort_key, "query": query_text}


def _set_pending_prefs(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    platform: Optional[str] = None,
    author: Optional[str] = None,
    sort_key: Optional[str] = None,
    query_text: Optional[str] = None,
) -> Dict[str, str]:
    prefs = _get_pending_prefs(context)
    if platform is not None:
        prefs["platform"] = platform
    if author is not None:
        prefs["author"] = author
    if sort_key is not None:
        prefs["sort"] = sort_key if sort_key in {SORT_NEWEST, SORT_TOP_SCORE, SORT_MOST_LIKES} else DEFAULT_SORT
    if query_text is not None:
        prefs["query"] = query_text.strip().lower()
    context.user_data[PENDING_PREFS_KEY] = prefs
    return prefs


def _apply_pending_filters(
    posts: List[Dict[str, object]],
    platform: str,
    query_text: str,
    sort_key: str,
    author: str = "",
) -> List[Dict[str, object]]:
    filtered = posts

    if platform == "other":
        known = {"instagram", "twitter", "youtube"}
        filtered = [p for p in filtered if str(p.get("platform", "")).lower() not in known]
    elif platform:
        filtered = [p for p in filtered if str(p.get("platform", "")).lower() == platform]

    if author:
        author_l = author.lower()
        filtered = [p for p in filtered if str(p.get("author", "")).lower() == author_l]

    if query_text:
        q = query_text.lower()
        filtered = [
            p
            for p in filtered
            if q in str(p.get("content", "")).lower()
            or q in str(p.get("author", "")).lower()
            or q in str(p.get("platform", "")).lower()
            or q in str(p.get("target_account", "")).lower()
        ]

    if sort_key == SORT_TOP_SCORE:
        filtered.sort(key=lambda p: float(p.get("engagement_score", 0.0) or 0.0), reverse=True)
    elif sort_key == SORT_MOST_LIKES:
        filtered.sort(key=lambda p: int(p.get("likes", 0) or 0), reverse=True)
    else:
        filtered.sort(key=lambda p: str(p.get("created_at", "")), reverse=True)

    return filtered


async def _send_filtered_pending_page(
    message: Message,
    prefs: Dict[str, str],
    offset: int,
    header: str = "Pending posts",
) -> None:
    """Send one page of filtered pending posts with navigation."""
    filtered_posts = _apply_pending_filters(
        posts=get_pending(),
        platform=prefs["platform"],
        query_text=prefs["query"],
        sort_key=prefs["sort"],
        author=prefs.get("author", ""),
    )
    total = len(filtered_posts)
    author_suffix = f" | @{prefs['author']}" if prefs.get("author") else ""
    query_suffix = f" | query: {prefs['query']}" if prefs.get("query") else ""
    await message.reply_text(
        f"{header}{author_suffix}\nSort: {_sort_label(prefs['sort'])}{query_suffix}",
        reply_markup=_build_pending_controls_keyboard(prefs["platform"], prefs["sort"], offset),
    )
    if total == 0:
        await message.reply_text("No pending posts for this filter.")
        return

    bounded_offset = max(0, min(offset, max(0, total - 1)))
    page = filtered_posts[bounded_offset : bounded_offset + PAGE_SIZE]
    for post in page:
        await _send_post_preview_to_message(message, post)

    next_offset = bounded_offset + PAGE_SIZE
    nav_rows: List[List[InlineKeyboardButton]] = []
    platform = prefs["platform"]
    if bounded_offset > 0:
        prev_offset = max(0, bounded_offset - PAGE_SIZE)
        nav_rows.append(
            [InlineKeyboardButton("◀ Prev", callback_data=f"pending_filter|{platform}|{prev_offset}")]
        )
    if next_offset < total:
        nav_rows.append([InlineKeyboardButton("Next ▶", callback_data=f"pending_filter|{platform}|{next_offset}")])
    if nav_rows:
        await message.reply_text(
            f"Showing {bounded_offset + 1}-{min(next_offset, total)} of {total}.",
            reply_markup=InlineKeyboardMarkup(nav_rows),
        )


async def _send_pending_page(message: Message, platform: str, offset: int) -> None:
    if not message:
        return
    posts = get_pending()
    if platform == "other":
        known = {"instagram", "twitter", "youtube"}
        posts = [p for p in posts if str(p.get("platform", "")).lower() not in known]
    elif platform:
        posts = [p for p in posts if str(p.get("platform", "")).lower() == platform]
    total = len(posts)
    if total == 0:
        await message.reply_text("No pending posts for this source.")
        return
    offset = max(0, min(offset, max(0, total)))
    page = posts[offset : offset + PAGE_SIZE]
    for post in page:
        await _send_post_preview_to_message(message, post)

    next_offset = offset + PAGE_SIZE
    nav_rows: List[List[InlineKeyboardButton]] = []
    if offset > 0:
        prev_offset = max(0, offset - PAGE_SIZE)
        nav_rows.append(
            [InlineKeyboardButton("◀ Prev", callback_data=f"pending_filter|{platform}|{prev_offset}")]
        )
    if next_offset < total:
        nav_rows.append([InlineKeyboardButton("Next ▶", callback_data=f"pending_filter|{platform}|{next_offset}")])
    if nav_rows:
        await message.reply_text(
            f"Showing {offset + 1}-{min(next_offset, total)} of {total}.",
            reply_markup=InlineKeyboardMarkup(nav_rows),
        )


async def _send_post_preview_to_message(message: Message, post: Dict[str, object]) -> None:
    """Send one post card to a specific Telegram message thread."""
    text = _build_post_text(post)
    reply_markup = _build_action_keyboard(int(post["id"]))
    media_url = str(post.get("media_url") or "").strip()

    if media_url:
        try:
            await message.reply_photo(
                photo=media_url,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
        except Exception:
            logger.exception("Failed to send media preview for post %s", post.get("id"))

    try:
        await message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception:
        logger.exception("Markdown preview failed for post %s, falling back to plain text", post.get("id"))
        plain = "\n".join(
            [
                f"{post.get('platform', '').title()} | @{post.get('author', 'unknown')}",
                f"Score: {float(post.get('engagement_score', 0) or 0):.1f}/100",
                "",
                _truncate_content(str(post.get("content", "")), 350),
            ]
        )
        await message.reply_text(text=plain, reply_markup=reply_markup)


async def _send_post_preview(update: Update, post: Dict[str, object]) -> None:
    """Send one post card as image+caption when possible."""
    if not update.effective_message:
        return
    await _send_post_preview_to_message(update.effective_message, post)


async def _lock_action_card(query: object) -> None:
    """Disable approve/reject buttons on the processed card."""
    try:
        await query.edit_message_reply_markup(reply_markup=None)  # type: ignore[attr-defined]
    except Exception:
        logger.debug("Unable to clear action buttons for processed post card.")


async def _move_to_next_pending(query: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the next pending post card, if available."""
    message = getattr(query, "message", None)
    if not message:
        return
    prefs = _get_pending_prefs(context)
    remaining = _apply_pending_filters(
        posts=get_pending(),
        platform=prefs["platform"],
        query_text=prefs["query"],
        sort_key=prefs["sort"],
        author=prefs.get("author", ""),
    )
    if not remaining:
        await message.reply_text("No more pending posts. You're all caught up.")
        return
    await message.reply_text("➡️ Moving to next pending post:")
    await _send_post_preview_to_message(message, remaining[0])


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle approve/reject/time slot callback actions."""
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()
    data = query.data or ""
    parts = _parse_callback(data)

    try:
        if parts[0] == "pending_menu":
            if not query.message:
                return
            prefs = _get_pending_prefs(context)
            await query.message.reply_text(
                "Choose platform and sort:",
                reply_markup=_build_pending_controls_keyboard(prefs["platform"], prefs["sort"], 0),
            )
            return

        if parts[0] == "pending_author" and len(parts) >= 2:
            platform = parts[1]
            author = parts[2] if len(parts) >= 3 else ""
            if not query.message:
                return
            prefs = _set_pending_prefs(context, platform=platform, author=author)
            title = f"{_platform_label(platform)} pending posts"
            if author:
                title = f"@{author} pending posts"
            await _send_filtered_pending_page(query.message, prefs, offset=0, header=title)
            return

        if parts[0] == "pending_filter" and len(parts) == 3:
            platform = parts[1]
            offset = int(parts[2])
            if not query.message:
                return
            prefs = _set_pending_prefs(context, platform=platform, author="")
            if offset == 0 and platform in {"twitter", "instagram"} and ACCOUNTS.get(platform):
                await query.message.reply_text(
                    f"Filter: {_platform_label(platform)}\nPick an account:",
                    reply_markup=_build_author_keyboard(platform),
                )
                return
            await _send_filtered_pending_page(
                query.message,
                prefs,
                offset=offset,
                header=f"{_platform_label(platform)} pending posts",
            )
            return

        if parts[0] == "pending_sort" and len(parts) == 2:
            sort_key = parts[1]
            if not query.message:
                return
            prefs = _set_pending_prefs(context, sort_key=sort_key)
            await query.message.reply_text(
                f"Sort changed to {_sort_label(prefs['sort'])}. Now choose source:",
                reply_markup=_build_pending_controls_keyboard(prefs["platform"], prefs["sort"], 0),
            )
            return

        if parts[0] == "approve" and len(parts) == 2:
            post_id = int(parts[1])
            default_time = get_default_time()
            _set_selected_date(context, post_id, _tomorrow_iso())
            date_iso = _get_selected_date(context, post_id)
            await query.message.reply_text(
                "\n".join(
                    [
                        "📅 *When should this go out\\?*",
                        "",
                        f"Date: *{_md(date_iso)}*",
                        f"Last used: *{_md(format_time_display(default_time))}*",
                    ]
                ),
                reply_markup=_build_default_time_keyboard(post_id),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return

        if parts[0] == "reject" and len(parts) == 2:
            post_id = int(parts[1])
            if reject_post(post_id):
                await _lock_action_card(query)
                await query.message.reply_text(f"❌ Rejected post #{post_id}.")
                await _move_to_next_pending(query, context)
            else:
                await query.message.reply_text(f"Could not reject post #{post_id}.")
            return

        if parts[0] == "use_default_time" and len(parts) == 2:
            post_id = int(parts[1])
            time_slot = get_default_time()
            date_iso = _get_selected_date(context, post_id)
            if schedule_post(post_id, date_iso, time_slot):
                await _lock_action_card(query)
                set_default_time(time_slot)
                post = get_post_by_id(post_id)
                author = str(post.get("author")) if post else "unknown"
                platform = str(post.get("platform", "")).title() if post else "Unknown"
                calendar_link = _calendar_link()
                await query.message.reply_text(
                    "\n".join(
                        [
                            "✅ *Scheduled\\!*",
                            "",
                            f"{_md(author)} — {_md(platform)}",
                            f"🗓 {_md(date_iso)} at {_md(format_time_display(time_slot))}",
                            "",
                            "View your schedule:",
                            f"👉 {_md(calendar_link)}",
                        ]
                    ),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                await _move_to_next_pending(query, context)
            else:
                await query.message.reply_text(f"Could not schedule post #{post_id}.")
            return

        if parts[0] == "change_time" and len(parts) == 2:
            post_id = int(parts[1])
            date_iso = _get_selected_date(context, post_id)
            await query.message.reply_text(
                f"Pick a posting time (date: {date_iso}):",
                reply_markup=_build_schedule_keyboard(post_id, date_iso),
            )
            return

        if parts[0] == "change_date" and len(parts) == 2:
            post_id = int(parts[1])
            await query.message.reply_text("Pick a date (next 7 days):", reply_markup=_build_date_keyboard(post_id))
            return

        if parts[0] == "select_date" and len(parts) == 3:
            post_id = int(parts[1])
            date_iso = parts[2]
            _set_selected_date(context, post_id, date_iso)
            await query.message.reply_text(
                f"Date set to {date_iso}. Now pick a time:",
                reply_markup=_build_schedule_keyboard(post_id, date_iso),
            )
            return

        if parts[0] == "set_default":
            time_slot: Optional[str] = None
            if len(parts) == 2:
                time_slot = parts[1]
            elif len(parts) == 3:
                time_slot = f"{parts[1]}:{parts[2]}"
            if not time_slot:
                await query.message.reply_text("Invalid time slot selected.")
                return
            if time_slot not in POST_TIMES:
                await query.message.reply_text("Invalid time slot selected.")
                return
            set_default_time(time_slot)
            await query.message.reply_text(f"✅ Default time set to {format_time_display(time_slot)}.")
            return

        if parts[0] == "schedule":
            # New format: schedule|post_id|HH:MM|YYYY-MM-DD (safe)
            # Old format: schedule:post_id:HH:MM:YYYY-MM-DD (split into 5)
            if len(parts) == 4:
                post_id = int(parts[1])
                time_slot = parts[2]
                date_iso = parts[3]
            elif len(parts) == 5:
                post_id = int(parts[1])
                time_slot = f"{parts[2]}:{parts[3]}"
                date_iso = parts[4]
            else:
                await query.message.reply_text("Invalid schedule action.")
                return
            if time_slot not in POST_TIMES:
                await query.message.reply_text("Invalid time slot selected.")
                return
            if reschedule_post(post_id, date_iso, time_slot):
                await _lock_action_card(query)
                set_default_time(time_slot)
                post = get_post_by_id(post_id)
                author = str(post.get("author")) if post else "unknown"
                platform = str(post.get("platform", "")).title() if post else "Unknown"
                calendar_link = _calendar_link()
                await query.message.reply_text(
                    "\n".join(
                        [
                            "✅ *Scheduled\\!*",
                            "",
                            f"{_md(author)} — {_md(platform)}",
                            f"🗓 {_md(date_iso)} at {_md(format_time_display(time_slot))}",
                            "",
                            "View your schedule:",
                            f"👉 {_md(calendar_link)}",
                        ]
                    ),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                await _move_to_next_pending(query, context)
            else:
                await query.message.reply_text(f"Could not schedule post #{post_id}.")
            return
    except Exception:
        logger.exception("Failed processing callback data: %s", data)
        await query.message.reply_text("⚠️ Something went wrong, try /pending again")
        return

    await query.message.reply_text("Unknown action.")


def register_handlers(application: Application) -> None:
    """Attach all command and callback handlers to the app."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("panding", pending_command))
    application.add_handler(CommandHandler("insta", insta_command))
    application.add_handler(CommandHandler("twitter", twitter_command))
    application.add_handler(CommandHandler("youtube", youtube_command))
    application.add_handler(CommandHandler("other", other_command))
    application.add_handler(CommandHandler("all", all_command))
    application.add_handler(CommandHandler("filter", filter_command))
    application.add_handler(CommandHandler("clearfilter", clearfilter_command))
    application.add_handler(CommandHandler("schedule", schedule_command))
    application.add_handler(CommandHandler("scheduled", scheduled_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("preview", preview_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("settime", settime_command))
    application.add_handler(CommandHandler("scrape", scrape_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CallbackQueryHandler(callback_router))
