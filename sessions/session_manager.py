# Module: session_manager | Purpose: Manage Playwright persistent browser sessions.
# Public API: SessionManager

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, Playwright, async_playwright

logger = logging.getLogger(__name__)

SESSIONS_ROOT = Path(__file__).resolve().parent
METADATA_FILE = "session_meta.json"

# URLs and selectors used to verify a logged-in state for each platform.
PLATFORM_CONFIG: Dict[str, Dict[str, str]] = {
    "instagram": {
        "base_url": "https://www.instagram.com/",
        "logged_in_selector": 'svg[aria-label="Home"], svg[aria-label="Search"]',
        "login_help": (
            "🔐 Instagram: Please log in manually in the browser window.\n"
            "   After you see the home feed, come back here and press ENTER."
        ),
    },
    "twitter": {
        "base_url": "https://x.com/home",
        "logged_in_selector": (
            'a[aria-label="Profile"], '
            '[data-testid="SideNav_AccountSwitcher_Button"], '
            '[data-testid="AppTabBar_Home_Link"]'
        ),
        "login_help": (
            "🔐 X/Twitter: Please log in manually in the browser window.\n"
            "   After you see the home timeline, come back here and press ENTER."
        ),
    },
    "youtube": {
        "base_url": "https://studio.youtube.com/",
        "logged_in_selector": 'ytcp-button[id="create-icon"], #avatar-btn',
        "login_help": (
            "🔐 YouTube: Please log in to your Google account in the browser.\n"
            "   After YouTube Studio loads, come back here and press ENTER."
        ),
    },
}

# Realistic browser fingerprint to reduce bot-detection.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


class SessionManager:
    """Handles persistent Playwright browser contexts per platform.

    Each platform gets its own profile directory under sessions/<platform>/,
    which stores the full browser state (cookies, localStorage, IndexedDB,
    service workers, etc.).  This avoids the fragility of cookie-only
    persistence.
    """

    def __init__(
        self,
        platform: str,
        headless: bool = False,
        viewport_width: int = 1280,
        viewport_height: int = 800,
    ) -> None:
        if platform not in PLATFORM_CONFIG:
            raise ValueError(
                f"Unknown platform '{platform}'. "
                f"Choose from: {', '.join(PLATFORM_CONFIG)}"
            )
        self.platform = platform
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

        self._profile_dir = SESSIONS_ROOT / platform
        self._meta_path = self._profile_dir / METADATA_FILE

        self._playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    async def start(self) -> BrowserContext:
        """Launch a persistent browser context reusing the stored profile."""
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()

        self.context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._profile_dir),
            headless=self.headless,
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            user_agent=DEFAULT_USER_AGENT,
            locale="en-US",
            timezone_id="Asia/Kolkata",
            # Permissions that social sites commonly request
            permissions=["notifications"],
            # Bypass some bot-detection signals
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
        )
        logger.info("Persistent context for '%s' started.", self.platform)
        return self.context

    async def close(self) -> None:
        """Close browser and Playwright resources gracefully."""
        if self.context:
            await self.context.close()
            self.context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Session for '%s' closed.", self.platform)

    # ------------------------------------------------------------------ #
    #  Login verification
    # ------------------------------------------------------------------ #

    async def is_logged_in(self) -> bool:
        """Navigate to platform and check if the session is still valid."""
        if not self.context:
            raise RuntimeError("Context not started. Call start() first.")

        cfg = PLATFORM_CONFIG[self.platform]
        page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        try:
            await page.goto(cfg["base_url"], wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(3000)  # Let JS hydrate
            locator = page.locator(cfg["logged_in_selector"]).first
            await locator.wait_for(timeout=8_000)
            logger.info("✅ '%s' session is valid.", self.platform)
            return True
        except Exception:
            logger.info("❌ '%s' session is NOT valid / expired.", self.platform)
            return False

    # ------------------------------------------------------------------ #
    #  Interactive login (first-time setup)
    # ------------------------------------------------------------------ #

    async def interactive_login(self) -> bool:
        """Open the platform in visible browser and wait for user to log in.

        Returns True when user completes login successfully.
        """
        if not self.context:
            raise RuntimeError("Context not started. Call start() first.")

        cfg = PLATFORM_CONFIG[self.platform]
        page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        await page.goto(cfg["base_url"], wait_until="domcontentloaded", timeout=30_000)

        # Print instructions
        print()
        print("=" * 60)
        print(cfg["login_help"])
        print("=" * 60)
        print()

        input("⏳ Press ENTER here after you have logged in... ")

        # Verify the login worked
        try:
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            locator = page.locator(cfg["logged_in_selector"]).first
            await locator.wait_for(timeout=10_000)
            self._save_metadata(success=True)
            print(f"\n✅ {self.platform.title()} login saved successfully!\n")
            return True
        except Exception:
            print(f"\n❌ Could not verify {self.platform.title()} login. Please try again.\n")
            return False

    # ------------------------------------------------------------------ #
    #  Metadata helpers
    # ------------------------------------------------------------------ #

    def _save_metadata(self, success: bool) -> None:
        """Write a small metadata file recording when the session was saved."""
        meta = {
            "platform": self.platform,
            "last_login": datetime.now(timezone.utc).isoformat(),
            "verified": success,
        }
        self._meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Return session metadata, or None if no session exists."""
        if not self._meta_path.exists():
            return None
        try:
            return json.loads(self._meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def session_exists(self) -> bool:
        """Return True if a profile directory with metadata exists."""
        return self._meta_path.exists()

    @staticmethod
    def list_platforms() -> List[str]:
        """Return available platform names."""
        return list(PLATFORM_CONFIG.keys())
