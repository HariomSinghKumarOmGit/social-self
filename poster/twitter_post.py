# Module: twitter_post | Purpose: Publish tweets via user's real Chrome.
# Public API: post_to_twitter

from __future__ import annotations

import logging
from typing import Dict, Optional

from poster.browser_poster import BrowserPoster, post_result

logger = logging.getLogger(__name__)


async def post_to_twitter(text: str, media_path: Optional[str] = None) -> Dict[str, str]:
    """Post a tweet using user's logged-in Chrome."""
    poster = BrowserPoster(platform="twitter")
    try:
        await poster.start()
        page = await poster.open_tab("https://x.com/home")
        await poster.human_delay(2000, 3500)

        # Verify logged in
        logged_in = await poster.verify_logged_in(
            "https://x.com/home",
            'a[aria-label="Profile"], [data-testid="SideNav_AccountSwitcher_Button"]',
        )
        if not logged_in:
            return post_result(False, error="Not logged in to X/Twitter in Chrome")

        # Navigate to compose
        await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
        await poster.human_delay()

        # Type tweet
        composer = page.locator('[data-testid="tweetTextarea_0"]').first
        await composer.click()
        await composer.type(text, delay=30)
        await poster.human_delay()

        # Attach media if provided
        if media_path:
            await page.locator('input[type="file"]').first.set_input_files(media_path)
            await poster.human_delay(1500, 3000)

        # Click post
        await page.locator('[data-testid="tweetButton"]').first.click()
        await poster.human_delay(2500, 4000)

        return post_result(True, post_url="https://x.com/home")
    except Exception as exc:
        logger.exception("Twitter posting failed.")
        shot = await poster.screenshot_failure("tw_post_error")
        return post_result(False, error=f"{exc}; screenshot={shot}")
    finally:
        await poster.close()
