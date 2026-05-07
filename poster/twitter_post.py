# Module: twitter_post | Purpose: Publish tweets through Playwright.
# Public API: post_to_twitter

from __future__ import annotations

import logging
from typing import Dict, Optional

from poster.browser_poster import BrowserPoster, post_result

logger = logging.getLogger(__name__)


async def post_to_twitter(text: str, media_path: Optional[str] = None) -> Dict[str, str]:
    """Post a tweet with optional media attachment using persistent session."""
    poster = BrowserPoster(platform="twitter", headless=False)
    try:
        await poster.start()
        await poster.ensure_login(
            base_url="https://x.com/home",
            logged_in_selector='a[aria-label="Profile"], [data-testid="SideNav_AccountSwitcher_Button"]',
            login_help_text="Please complete X/Twitter login in the opened browser.",
        )
        assert poster.page is not None
        await poster.page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
        await poster.human_delay()

        composer = poster.page.locator('[data-testid="tweetTextarea_0"]').first
        await composer.click()
        await composer.type(text, delay=30)
        await poster.human_delay()

        if media_path:
            await poster.page.locator('input[type="file"]').first.set_input_files(media_path)
            await poster.human_delay(1500, 3000)

        await poster.page.locator('[data-testid="tweetButton"]').first.click()
        await poster.human_delay(2500, 4000)
        return post_result(True, post_url="https://x.com/home")
    except Exception as exc:
        logger.exception("Twitter posting failed.")
        shot = await poster.screenshot_failure("twitter_post_error")
        return post_result(False, error=f"{exc}; screenshot={shot}")
    finally:
        await poster.close()
