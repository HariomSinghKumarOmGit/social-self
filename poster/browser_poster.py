# Module: browser_poster | Purpose: Shared Playwright session and helper utilities.
# Public API: BrowserPoster, post_result

from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("sessions")
LOGS_DIR = Path("logs")


@dataclass
class BrowserPoster:
    """Shared Playwright wrapper with cookie/session helpers."""

    platform: str
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 800

    _playwright: Any = None
    _browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None

    async def start(self) -> None:
        """Start Playwright, browser, and a single page context."""
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self.context = await self._browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        )
        await self.load_session()
        self.page = await self.context.new_page()

    async def close(self) -> None:
        """Close browser resources gracefully."""
        if self.context:
            await self.context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @property
    def _cookie_path(self) -> Path:
        """Return platform cookie file path."""
        return SESSIONS_DIR / f"{self.platform}_cookies.json"

    async def save_session(self) -> None:
        """Persist current context cookies for future runs."""
        if not self.context:
            return
        cookies = await self.context.cookies()
        self._cookie_path.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        logger.info("Saved %s session cookies.", self.platform)

    async def load_session(self) -> bool:
        """Load persisted cookies into context if present."""
        if not self.context or not self._cookie_path.exists():
            return False
        try:
            cookies = json.loads(self._cookie_path.read_text(encoding="utf-8"))
            await self.context.add_cookies(cookies)
            logger.info("Loaded saved %s session.", self.platform)
            return True
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed loading %s cookies.", self.platform)
            return False

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
        """
        Navigate and ensure user is logged in.

        First run is expected to require manual login in visible browser mode.
        """
        if not self.page:
            raise RuntimeError("Browser not started.")
        await self.page.goto(base_url, wait_until="domcontentloaded")
        await self.human_delay()
        try:
            await self.page.locator(logged_in_selector).first.wait_for(timeout=5000)
            return
        except Exception:
            logger.info("%s", login_help_text)
            await self.page.pause()
            await self.save_session()


def post_result(success: bool, post_url: str = "", error: str = "") -> Dict[str, str]:
    """Standard response payload for posting functions."""
    return {
        "success": str(success),
        "post_url": post_url,
        "error": error,
    }
