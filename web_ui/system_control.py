"""Start and monitor local Social Agent processes."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIST = PROJECT_ROOT / "review-ui" / "dist"
BOT_SCRIPT = PROJECT_ROOT / "telegram_bot" / "bot.py"


def _port() -> str:
    return os.environ.get("PORT") or os.environ.get("WEB_UI_PORT") or "56823"


def _base_url() -> str:
    return f"http://127.0.0.1:{_port()}"


def _process_running(pattern: str) -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        logger.exception("Failed checking process: %s", pattern)
        return False


def get_system_status() -> Dict[str, Any]:
    """Return health of web UI, Telegram bot, and review build."""
    bot_running = _process_running("telegram_bot/bot.py")
    review_built = (REVIEW_DIST / "index.html").exists()
    port = _port()
    base = _base_url()
    return {
        "ok": True,
        "web": True,
        "bot": bot_running,
        "review_built": review_built,
        "port": port,
        "links": {
            "home": f"{base}/",
            "feed": f"{base}/feed",
            "review": f"{base}/review",
        },
        "message": "All systems running" if bot_running else "Telegram bot is stopped",
    }


def start_telegram_bot() -> Dict[str, Any]:
    """Start Telegram bot if not already running."""
    if os.environ.get("VERCEL"):
        return {
            "ok": False,
            "error": "Telegram bot cannot run on Vercel. Use Start Beast locally or a VPS.",
        }
    if _process_running("telegram_bot/bot.py"):
        return {"ok": True, "bot": "already_running", "message": "Telegram bot already running."}

    if not BOT_SCRIPT.exists():
        return {"ok": False, "error": "telegram_bot/bot.py not found"}

    env = os.environ.copy()
    env.setdefault("WEB_UI_PORT", _port())

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = open(log_dir / "telegram_bot.log", "a", encoding="utf-8")

    subprocess.Popen(
        [sys.executable, str(BOT_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return {"ok": True, "bot": "started", "message": "Telegram bot started."}


def start_beast() -> Dict[str, Any]:
    """One-click: ensure bot is up and return all dashboard links."""
    status = get_system_status()
    result: Dict[str, Any] = {
        "ok": True,
        "links": status["links"],
        "review_built": status["review_built"],
        "web": True,
    }

    if not status["bot"]:
        bot_result = start_telegram_bot()
        result["bot_action"] = bot_result
        if not bot_result.get("ok"):
            result["ok"] = False
            result["error"] = bot_result.get("error", "Failed to start bot")
        else:
            result["bot"] = True
            result["message"] = "Beast mode ON — web + Telegram bot are running."
    else:
        result["bot"] = True
        result["message"] = "Beast mode ON — everything already running."

    if not status["review_built"]:
        result["warning"] = (
            "Review UI not built. Run: cd review-ui && npm install && npm run build"
        )

    return result
