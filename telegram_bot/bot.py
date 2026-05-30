# Module: telegram_bot | Purpose: Bootstrap and run Telegram moderation bot.
# Public API: build_application, run_bot, run_bot_in_thread

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import IO

from telegram import Update
from telegram.ext import Application, ContextTypes
from telegram.error import Conflict

# Allow running as: python3 telegram_bot/bot.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from config import TELEGRAM_BOT_TOKEN
from telegram_bot.handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
# Avoid printing Telegram API URLs (they include bot token).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

_polling_lock_file: IO[str] | None = None


def _acquire_polling_lock() -> bool:
    """Hold a per-machine lock so this checkout starts only one polling loop."""
    global _polling_lock_file
    if _polling_lock_file is not None:
        return True
    if os.name != "posix":
        return True

    import fcntl

    lock_path = Path(os.environ.get("TELEGRAM_POLLING_LOCK_PATH", "/tmp/social_self_telegram_bot.lock"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        logger.warning("Telegram bot polling already running in this container; skipping startup.")
        return False

    lock_file.seek(0)
    lock_file.truncate()
    lock_file.write(str(os.getpid()))
    lock_file.flush()
    _polling_lock_file = lock_file
    return True


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unhandled bot errors and notify the user when possible."""
    if isinstance(context.error, Conflict):
        logger.error(
            "Telegram polling conflict (another bot instance is running). "
            "Stop the other instance and restart this one."
        )
        try:
            if context.application.updater:
                await context.application.updater.stop()
        finally:
            await context.application.stop()
            await context.application.shutdown()
        return
    logger.exception("Unhandled telegram error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("⚠️ Something went wrong. Try /pending again.")
        except Exception:
            logger.exception("Failed to send error notice to Telegram user.")


def build_application() -> Application:
    """Create bot application and register command/callback handlers."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Add it to your .env file.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(application)
    application.add_error_handler(_error_handler)
    return application


def run_bot() -> None:
    """Start long-polling bot process (main thread only — uses signal handlers)."""
    if not _acquire_polling_lock():
        return
    application = build_application()
    logger.info("Telegram bot started in polling mode.")
    try:
        application.run_polling(drop_pending_updates=True)
    except Conflict:
        logger.error(
            "Telegram polling conflict: another deployed/local instance is already calling "
            "getUpdates for this token. Stop the other instance or disable polling here."
        )


def run_bot_in_thread() -> None:
    """
    Start the bot in a non-main thread.

    python-telegram-bot's run_polling() installs signal handlers which
    require the main thread.  This helper manually drives the async
    lifecycle so it works from any daemon thread.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if not _acquire_polling_lock():
        loop.close()
        return
    application = build_application()

    async def _run() -> None:
        await application.initialize()
        try:
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot started (thread-safe polling).")
            # Block forever until the loop is stopped externally
            stop_event = asyncio.Event()
            await stop_event.wait()
        except Conflict:
            logger.error(
                "Telegram polling conflict: another deployed/local instance is already calling "
                "getUpdates for this token. Web UI will keep running without this bot poller."
            )
        finally:
            updater = application.updater
            if updater and getattr(updater, "running", False):
                await updater.stop()
            if getattr(application, "running", False):
                await application.stop()
            await application.shutdown()

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    run_bot()
