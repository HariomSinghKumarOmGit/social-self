# Module: telegram_handlers | Purpose: Callback and command handlers for moderation flow.
# Public API: register_handlers

from __future__ import annotations

import logging
from typing import Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import POST_TIMES
from database import approve_post, get_pending, get_post_by_id, get_scheduled, reject_post

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
    """Build time slot buttons after approve tap."""
    buttons = [
        [InlineKeyboardButton(time_slot, callback_data=f"schedule:{post_id}:{time_slot}")]
        for time_slot in POST_TIMES
    ]
    return InlineKeyboardMarkup(buttons)


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
        when = str(post.get("scheduled_time", "unscheduled"))
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
        f"Configured time slots: {', '.join(POST_TIMES)}"
    )


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
                "Pick a posting time:",
                reply_markup=_build_schedule_keyboard(post_id),
            )
            return

        if parts[0] == "reject" and len(parts) == 2:
            post_id = int(parts[1])
            if reject_post(post_id):
                await query.message.reply_text(f"❌ Rejected post #{post_id}.")
            else:
                await query.message.reply_text(f"Could not reject post #{post_id}.")
            return

        if parts[0] == "schedule" and len(parts) == 3:
            post_id = int(parts[1])
            time_slot = parts[2]
            if time_slot not in POST_TIMES:
                await query.message.reply_text("Invalid time slot selected.")
                return
            if approve_post(post_id, time_slot):
                post = get_post_by_id(post_id)
                author = str(post.get("author")) if post else "unknown"
                await query.message.reply_text(
                    f"✅ Approved post #{post_id} by @{author} for {time_slot}."
                )
            else:
                await query.message.reply_text(f"Could not approve post #{post_id}.")
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
    application.add_handler(CallbackQueryHandler(callback_router))
