# Module: browser_poster | Purpose: Post to social platforms via user's real Chrome.
# Public API: BrowserPoster
#
# This connects to user's actual Chrome (via CDP) and posts directly.
# No separate browser, no login needed — uses existing sessions.

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from playwright.async_api import Page

from sessions.browser_bridge import BrowserBridge

logger = logging.getLogger(__name__)

LOGS_DIR = Path("logs")


class BrowserPoster:
    """Post content using the user's real Chrome browser.

    Connects via CDP to the user's Chrome (where they're already logged in),
    opens a new tab, performs the posting action, and closes the tab.
    """

    def __init__(self, platform: str, bridge: Optional[BrowserBridge] = None) -> None:
        self.platform = platform
        self._bridge = bridge
        self._own_bridge = bridge is None
        self.page: Optional[Page] = None

    async def start(self) -> None:
        """Connect to user's Chrome and open a new tab."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if self._own_bridge:
            self._bridge = BrowserBridge()
            await self._bridge.connect()

    async def close(self) -> None:
        """Close our tab and disconnect (doesn't close user's Chrome)."""
        if self.page and self._bridge:
            await self._bridge.close_tab(self.page)
            self.page = None
        if self._own_bridge and self._bridge:
            await self._bridge.disconnect()

    async def open_tab(self, url: str) -> Page:
        """Open a new tab and navigate to url."""
        if not self._bridge:
            raise RuntimeError("Not connected. Call start() first.")
        self.page = await self._bridge.new_tab(url)
        return self.page

    async def human_delay(self, low_ms: int = 800, high_ms: int = 2500) -> None:
        """Random delay to mimic human behavior."""
        await asyncio.sleep(random.uniform(low_ms / 1000.0, high_ms / 1000.0))

    async def screenshot_failure(self, prefix: str) -> str:
        """Save a debug screenshot."""
        if not self.page or not self._bridge:
            return ""
        return await self._bridge.screenshot(self.page, prefix)

    async def verify_logged_in(self, url: str, selector: str) -> bool:
        """Check if the user is logged in on the given platform."""
        if not self.page:
            self.page = await self.open_tab(url)
        else:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=20_000)

        await self.human_delay(2000, 3000)
        try:
            await self.page.locator(selector).first.wait_for(timeout=8_000)
            logger.info("✅ Logged in to %s", self.platform)
            return True
        except Exception:
            logger.warning("❌ Not logged in to %s in this Chrome session", self.platform)
            return False


def post_result(success: bool, post_url: str = "", error: str = "") -> Dict[str, str]:
    """Standard response payload for posting functions."""
    return {
        "success": str(success),
        "post_url": post_url,
        "error": error,
    }
