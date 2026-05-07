# Module: browser_poster | Purpose: Shared Playwright session and helper utilities.
# Public API: BrowserPoster, post_result

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

logger = logging.getLogger(__name__)

SESSIONS_ROOT = Path(__file__).resolve().parent.parent / "sessions"
LOGS_DIR = Path("logs")


@dataclass
class BrowserPoster:
    """Shared Playwright wrapper using persistent browser context.

    Instead of saving/loading cookies, this uses Playwright's
    ``launch_persistent_context`` which preserves the full browser state
    (cookies, localStorage, IndexedDB, service workers, etc.) across runs.
    """

    platform: str
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 800

    _playwright: Optional[Playwright] = field(default=None, repr=False)
    context: Optional[BrowserContext] = field(default=None, repr=False)
    page: Optional[Page] = field(default=None, repr=False)

    async def start(self) -> None:
        """Start Playwright with a persistent browser context for the platform."""
        profile_dir = SESSIONS_ROOT / self.platform
        profile_dir.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()

        self.context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.headless,
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Asia/Kolkata",
            permissions=["notifications"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
        )
        # Reuse existing tab or open a new one
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def close(self) -> None:
        """Close browser resources gracefully."""
        if self.context:
            await self.context.close()
        if self._playwright:
            await self._playwright.stop()

    async def human_delay(self, low_ms: int = 1000, high_ms: int = 3000) -> None:
        """Wait random delay to look less bot-like."""
        await asyncio.sleep(random.uniform(low_ms / 1000.0, high_ms / 1000.0))

    async def screenshot_failure(self, prefix: str) -> str:
        """Capture screenshot to logs for debugging."""
        if not self.page:
            return ""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = LOGS_DIR / f"{prefix}_{ts}.png"
        await self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    async def ensure_login(
        self, base_url: str, logged_in_selector: str, login_help_text: str
    ) -> None:
        """Navigate and verify user is logged in via persistent session.

        Since sessions are now persistent (full browser profile), re-login
        should be very rare. If session has expired, the user will be
        prompted to re-run:  python -m sessions.login_setup <platform>
        """
        if not self.page:
            raise RuntimeError("Browser not started.")
        await self.page.goto(base_url, wait_until="domcontentloaded")
        await self.human_delay()
        try:
            await self.page.locator(logged_in_selector).first.wait_for(timeout=10_000)
            logger.info("✅ %s session is active.", self.platform)
        except Exception:
            logger.warning(
                "❌ %s session expired or not set up. "
                "Run:  python -m sessions.login_setup %s",
                self.platform,
                self.platform,
            )
            raise RuntimeError(
                f"{self.platform} session not valid. "
                f"Run:  python -m sessions.login_setup {self.platform}"
            )


def post_result(success: bool, post_url: str = "", error: str = "") -> Dict[str, str]:
    """Standard response payload for posting functions."""
    return {
        "success": str(success),
        "post_url": post_url,
        "error": error,
    }
