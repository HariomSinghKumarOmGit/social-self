# Module: browser_bridge | Purpose: Connect to user's real Chrome via CDP.
# Public API: BrowserBridge
#
# This is the OBS-style "overlay" concept — instead of launching a new
# browser, we attach to the user's *existing* Chrome session where they
# are already logged in to Instagram, X/Twitter, YouTube, etc.
#
# HOW IT WORKS:
#   1. User starts Chrome with:  --remote-debugging-port=9222
#   2. BrowserBridge connects via CDP (Chrome DevTools Protocol)
#   3. Opens new TABS in the same browser for scraping / posting
#   4. Closes tabs when done — user's browsing is unaffected

from __future__ import annotations

import asyncio
import logging
import platform
import random
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

logger = logging.getLogger(__name__)

LOGS_DIR = Path("logs")

# Default CDP endpoint
DEFAULT_CDP_URL = "http://127.0.0.1:9222"

# Chrome executable paths by OS
CHROME_PATHS = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ],
    "Linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ],
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
}


def _find_chrome() -> Optional[str]:
    """Find Chrome executable on the system."""
    os_name = platform.system()
    for path in CHROME_PATHS.get(os_name, []):
        if Path(path).exists():
            return path
    return None


def launch_chrome_debug(port: int = 9222) -> Optional[subprocess.Popen]:
    """Launch Chrome with remote debugging enabled.

    This only needs to be done ONCE. After Chrome is running with
    --remote-debugging-port, the agent can connect to it anytime.

    Returns the subprocess handle, or None if Chrome wasn't found.
    """
    chrome_path = _find_chrome()
    if not chrome_path:
        logger.error(
            "Chrome not found. Please start Chrome manually with:\n"
            '  "/path/to/chrome" --remote-debugging-port=%s',
            port,
        )
        return None

    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        # Keep user's existing profile — this is key!
        # By NOT specifying --user-data-dir, Chrome uses the default profile
        # where the user is already logged in to everything.
    ]
    logger.info("Launching Chrome with debugging on port %s", port)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc


class BrowserBridge:
    """Connect to user's running Chrome via CDP and operate in new tabs.

    Think of this like OBS — it works ON TOP of your existing browser.
    Your sessions, cookies, logins — everything is already there.

    Usage:
        bridge = BrowserBridge()
        await bridge.connect()
        page = await bridge.new_tab("https://instagram.com")
        # ... do stuff ...
        await bridge.close_tab(page)
        await bridge.disconnect()
    """

    def __init__(self, cdp_url: str = DEFAULT_CDP_URL) -> None:
        self.cdp_url = cdp_url
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._managed_pages: list[Page] = []

    # ------------------------------------------------------------------
    #  Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to user's Chrome via CDP."""
        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
            contexts = self._browser.contexts
            logger.info(
                "✅ Connected to Chrome (CDP). Found %s context(s), %s total tab(s).",
                len(contexts),
                sum(len(ctx.pages) for ctx in contexts),
            )
        except Exception as exc:
            await self._playwright.stop()
            self._playwright = None
            raise ConnectionError(
                f"Could not connect to Chrome at {self.cdp_url}. "
                f"Make sure Chrome is running with: --remote-debugging-port=9222. "
                f"Underlying error: {type(exc).__name__}"
            ) from None

    async def disconnect(self) -> None:
        """Disconnect from Chrome (does NOT close the user's browser)."""
        # Close only our managed tabs
        for page in self._managed_pages:
            try:
                if not page.is_closed():
                    await page.close()
            except Exception:
                pass
        self._managed_pages.clear()

        if self._browser:
            # disconnect() detaches without closing user's Chrome
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Disconnected from Chrome. User's browser is untouched.")

    @property
    def is_connected(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    # ------------------------------------------------------------------
    #  Tab management
    # ------------------------------------------------------------------

    def _default_context(self) -> BrowserContext:
        """Get the user's default browser context (where they're logged in)."""
        if not self._browser:
            raise RuntimeError("Not connected. Call connect() first.")
        contexts = self._browser.contexts
        if not contexts:
            raise RuntimeError("No browser context found. Is Chrome running?")
        return contexts[0]  # Default context = user's main profile

    async def new_tab(self, url: Optional[str] = None) -> Page:
        """Open a new tab in user's browser. Optionally navigate to url."""
        ctx = self._default_context()
        page = await ctx.new_page()
        self._managed_pages.append(page)

        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await self.human_delay(1000, 2000)

        logger.info("Opened new tab%s", f": {url}" if url else "")
        return page

    async def close_tab(self, page: Page) -> None:
        """Close a tab we opened (never closes user's existing tabs)."""
        if page in self._managed_pages:
            self._managed_pages.remove(page)
        if not page.is_closed():
            await page.close()

    # ------------------------------------------------------------------
    #  Utilities
    # ------------------------------------------------------------------

    async def human_delay(self, low_ms: int = 800, high_ms: int = 2500) -> None:
        """Random delay to mimic human behavior."""
        await asyncio.sleep(random.uniform(low_ms / 1000.0, high_ms / 1000.0))

    async def human_type(self, page: Page, selector: str, text: str, delay: int = 35) -> None:
        """Type text like a human — character by character with random delays."""
        el = page.locator(selector).first
        await el.click()
        await el.type(text, delay=delay)

    async def screenshot(self, page: Page, prefix: str) -> str:
        """Save a debug screenshot and return the path."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = LOGS_DIR / f"{prefix}_{ts}.png"
        await page.screenshot(path=str(path), full_page=True)
        logger.info("Screenshot saved: %s", path)
        return str(path)

    async def scroll_down(self, page: Page, times: int = 3, delay_ms: int = 1000) -> None:
        """Scroll down a page to trigger lazy-loading content."""
        for _ in range(times):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay_ms / 1000.0)

    async def wait_for_network_idle(self, page: Page, timeout: int = 10_000) -> None:
        """Wait for network to settle (useful after navigation)."""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass  # Timeout is OK — some pages never truly go idle
