# Module: telegram_handlers | Purpose: Callback and command handlers for moderation flow.
# Public API: register_handlers

from __future__ import annotations

import logging
from typing import Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import EC2_PUBLIC_IP, POST_TIMES
from database import (
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

PLATFORM_ICONS = {
    "instagram": "📸",
    "twitter": "🐦",
    "youtube": "📺",
}


def _truncate_content(text: str, limit: int = 200) -> str:
    """Return a short content preview for Telegram messages."""
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else f"{cleaned[: limit - 3]}..."


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
    return (
        f"{icon} {platform.title()} | @{author}\n"
        f"Score: {score:.2f}/100\n"
        f"👍 {likes} | 💬 {comments} | 🔁 {shares} | 🔖 {saves}\n\n"
        f"{preview}"
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


def _build_schedule_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Build full time slot buttons (used after Change)."""
    date_iso = _today_iso()
    buttons = []
    for time_slot in POST_TIMES:
        if not time_slot:
            continue
        label = format_time_display(time_slot)
        buttons.append([InlineKeyboardButton(label, callback_data=f"schedule:{post_id}:{time_slot}:{date_iso}")])
    return InlineKeyboardMarkup(buttons)


def _build_default_time_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Build default time confirmation keyboard shown right after Approve."""
    default_time = get_default_time()
    label = f"⭐ Use {format_time_display(default_time)}"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(label, callback_data=f"use_default_time:{post_id}")],
            [InlineKeyboardButton("🕐 Change time", callback_data=f"change_time:{post_id}")],
        ]
    )


def _today_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).date().isoformat()


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
        "/scheduled - show approved queue\n"
        "/status - queue health summary\n"
        "/settime - set your default posting time\n"
        "/help - show command list"
    )


async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render all pending posts with moderation buttons."""
    del context
    if not update.effective_message:
        return

    posts = get_pending()
    if not posts:
        await update.effective_message.reply_text("No pending posts right now.")
        return

    await update.effective_message.reply_text(f"Found {len(posts)} pending posts.")
    for post in posts:
        await _send_post_preview(update, post)


async def scheduled_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show approved posts that already have a selected schedule time."""
    del context
    if not update.effective_message:
        return

    posts = get_scheduled()
    if not posts:
        await update.effective_message.reply_text("No approved scheduled posts right now.")
        return

    lines = ["Approved queue:"]
    for post in posts:
        post_id = int(post.get("id", 0) or 0)
        platform = str(post.get("platform", "")).title()
        author = str(post.get("author", "unknown"))
        date_s = str(post.get("scheduled_date") or "")
        time_s = str(post.get("scheduled_time") or "")
        when = f"{date_s} {time_s}".strip() or "unscheduled"
        lines.append(f"#{post_id} | {platform} | @{author} | {when}")
    await update.effective_message.reply_text("\n".join(lines[:80]))


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
        [[InlineKeyboardButton(format_time_display(t), callback_data=f"set_default:{t}")] for t in POST_TIMES]
    )
    await update.effective_message.reply_text("Pick your default posting time:", reply_markup=keyboard)


async def _send_post_preview(update: Update, post: Dict[str, object]) -> None:
    """Send one post card as image+caption when possible."""
    if not update.effective_message:
        return

    text = _build_post_text(post)
    reply_markup = _build_action_keyboard(int(post["id"]))
    media_url = str(post.get("media_url") or "").strip()

    if media_url:
        try:
            await update.effective_message.reply_photo(
                photo=media_url,
                caption=text,
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.exception("Failed to send media preview for post %s", post.get("id"))

    await update.effective_message.reply_text(text=text, reply_markup=reply_markup)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle approve/reject/time slot callback actions."""
    del context
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()
    data = query.data or ""
    parts = data.split(":")

    try:
        if parts[0] == "approve" and len(parts) == 2:
            post_id = int(parts[1])
            await query.message.reply_text(
                f"📅 When should this go out?\n\nLast used: {format_time_display(get_default_time())}",
                reply_markup=_build_default_time_keyboard(post_id),
            )
            return

        if parts[0] == "reject" and len(parts) == 2:
            post_id = int(parts[1])
            if reject_post(post_id):
                await query.message.reply_text(f"❌ Rejected post #{post_id}.")
            else:
                await query.message.reply_text(f"Could not reject post #{post_id}.")
            return

        if parts[0] == "use_default_time" and len(parts) == 2:
            post_id = int(parts[1])
            time_slot = get_default_time()
            date_iso = _today_iso()
            if schedule_post(post_id, date_iso, time_slot):
                set_default_time(time_slot)
                post = get_post_by_id(post_id)
                author = str(post.get("author")) if post else "unknown"
                platform = str(post.get("platform", "")).title() if post else "Unknown"
                calendar_link = f"http://{EC2_PUBLIC_IP}:5000" if EC2_PUBLIC_IP else "http://localhost:5000"
                await query.message.reply_text(
                    "✅ Scheduled!\n\n"
                    f"{author} — {platform}\n"
                    f"🗓 {date_iso} at {format_time_display(time_slot)}\n\n"
                    f"View your schedule:\n👉 {calendar_link}"
                )
            else:
                await query.message.reply_text(f"Could not schedule post #{post_id}.")
            return

        if parts[0] == "change_time" and len(parts) == 2:
            post_id = int(parts[1])
            await query.message.reply_text("Pick a posting time:", reply_markup=_build_schedule_keyboard(post_id))
            return

        if parts[0] == "set_default" and len(parts) == 2:
            time_slot = parts[1]
            if time_slot not in POST_TIMES:
                await query.message.reply_text("Invalid time slot selected.")
                return
            set_default_time(time_slot)
            await query.message.reply_text(f"✅ Default time set to {format_time_display(time_slot)}.")
            return

        if parts[0] == "schedule" and len(parts) == 4:
            post_id = int(parts[1])
            time_slot = parts[2]
            date_iso = parts[3]
            if time_slot not in POST_TIMES:
                await query.message.reply_text("Invalid time slot selected.")
                return
            if reschedule_post(post_id, date_iso, time_slot):
                set_default_time(time_slot)
                post = get_post_by_id(post_id)
                author = str(post.get("author")) if post else "unknown"
                platform = str(post.get("platform", "")).title() if post else "Unknown"
                calendar_link = f"http://{EC2_PUBLIC_IP}:5000" if EC2_PUBLIC_IP else "http://localhost:5000"
                await query.message.reply_text(
                    "✅ Scheduled!\n\n"
                    f"{author} — {platform}\n"
                    f"🗓 {date_iso} at {format_time_display(time_slot)}\n\n"
                    f"View your schedule:\n👉 {calendar_link}"
                )
            else:
                await query.message.reply_text(f"Could not schedule post #{post_id}.")
            return
    except Exception:
        logger.exception("Failed processing callback data: %s", data)
        await query.message.reply_text("Something went wrong. Please try again.")
        return

    await query.message.reply_text("Unknown action.")


def register_handlers(application: Application) -> None:
    """Attach all command and callback handlers to the app."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("scheduled", scheduled_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("settime", settime_command))
    application.add_handler(CallbackQueryHandler(callback_router))
