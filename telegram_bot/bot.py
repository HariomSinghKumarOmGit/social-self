# Module: telegram_bot | Purpose: Bootstrap and run Telegram moderation bot.
# Public API: build_application, run_bot

from __future__ import annotations

import logging
import sys
from pathlib import Path

from telegram.ext import Application, ContextTypes

# Allow running as: python3 telegram_bot/bot.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import TELEGRAM_BOT_TOKEN
from telegram_bot.handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unhandled bot errors without crashing polling."""
    del update
    logger.exception("Unhandled telegram error: %s", context.error)


def build_application() -> Application:
    """Create bot application and register command/callback handlers."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Add it to your .env file.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(application)
    application.add_error_handler(_error_handler)
    return application


def run_bot() -> None:
    """Start long-polling bot process."""
    application = build_application()
    logger.info("Telegram bot started in polling mode.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
