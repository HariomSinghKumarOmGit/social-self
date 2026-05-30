#!/usr/bin/env python3
# Module: main | Purpose: Entry point — runs Web UI, Telegram bot, and Scheduler.
# Public API: main

from __future__ import annotations

import logging
import os
import signal
import socket
import sys
import threading
from typing import NoReturn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = r"""
╔═══════════════════════════════════════════════════════════╗
║           🧠  SOCIAL MEDIA AUTOMATION AGENT  🧠          ║
╠═══════════════════════════════════════════════════════════╣
║  Components:                                             ║
║    📅  Flask Calendar UI        http://{ip}:{port}      ║
║    🤖  Telegram Bot             polling mode             ║
║    ⏱️   Scheduler                scrape every 24h       ║
╠═══════════════════════════════════════════════════════════╣
║  Press Ctrl+C to shut down gracefully.                   ║
╚═══════════════════════════════════════════════════════════╝
"""


def _get_local_ip() -> str:
    """Best-effort local network IP detection."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# Thread starters
# ---------------------------------------------------------------------------

_shutdown_event = threading.Event()


def _start_flask() -> None:
    """Run Flask as the foreground HTTP server."""
    from web_ui.app import app

    port = int(os.environ.get("PORT", "5001"))
    logger.info("Starting Flask on 0.0.0.0:%s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def _start_telegram_bot() -> None:
    """Run Telegram bot polling in a daemon thread (thread-safe version)."""
    if os.environ.get("TELEGRAM_POLLING_ENABLED", "1").lower() in {"0", "false", "no"}:
        logger.info("Telegram bot polling disabled by TELEGRAM_POLLING_ENABLED.")
        return
    try:
        from telegram_bot.bot import run_bot_in_thread

        logger.info("Starting Telegram bot polling.")
        run_bot_in_thread()
    except Exception:
        logger.exception("Telegram bot thread crashed.")


def _start_scheduler() -> None:
    """Run the scheduler loop in a daemon thread."""
    try:
        from scheduler import start_scheduler

        start_scheduler()
    except Exception:
        logger.exception("Scheduler thread crashed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _shutdown_handler(signum, frame):
    """Handle Ctrl+C / SIGTERM cleanly."""
    logger.info("Shutdown signal received (signal=%s). Stopping…", signum)
    _shutdown_event.set()
    sys.exit(0)


def main() -> NoReturn:
    """Launch background workers, then run the HTTP server in the main thread."""
    os.environ["SOCIAL_AGENT_EMBEDDED_BOT"] = "1"
    os.environ["SOCIAL_AGENT_EMBEDDED_SCHEDULER"] = "1"
    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    ip = _get_local_ip()
    print(BANNER.format(ip=ip, port=os.environ.get("PORT", "5001")))

    background_threads = [
        threading.Thread(target=_start_telegram_bot, name="telegram-bot", daemon=True),
        threading.Thread(target=_start_scheduler, name="scheduler", daemon=True),
    ]

    for t in background_threads:
        t.start()
        logger.info("Thread [%s] started.", t.name)

    try:
        _start_flask()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("HTTP server stopped; daemon workers will exit with the process.")
        sys.exit(0)


if __name__ == "__main__":
    main()
