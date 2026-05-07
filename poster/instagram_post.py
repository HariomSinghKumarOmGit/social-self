# Module: instagram_post | Purpose: Publish Instagram posts through Playwright.
# Public API: post_to_instagram

from __future__ import annotations

import logging
from typing import Dict

from poster.browser_poster import BrowserPoster, post_result

logger = logging.getLogger(__name__)


async def post_to_instagram(image_path: str, caption: str) -> Dict[str, str]:
    """Upload an image post to Instagram Web using persistent session."""
    poster = BrowserPoster(platform="instagram", headless=False)
    try:
        await poster.start()
        await poster.ensure_login(
            base_url="https://www.instagram.com/",
            logged_in_selector='svg[aria-label="Home"]',
            login_help_text="Please complete Instagram login in the opened browser.",
        )
        assert poster.page is not None
        await poster.page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        await poster.human_delay()

        await poster.page.locator('svg[aria-label="New post"], div[role="menuitem"]').first.click()
        await poster.human_delay()
        await poster.page.locator('input[type="file"]').set_input_files(image_path)
        await poster.human_delay()

        for _ in range(2):
            next_btn = poster.page.get_by_role("button", name="Next")
            await next_btn.click()
            await poster.human_delay()

        caption_box = poster.page.locator('div[aria-label="Write a caption..."]').first
        await caption_box.click()
        await caption_box.type(caption, delay=40)
        await poster.human_delay()
        await poster.page.get_by_role("button", name="Share").click()
        await poster.human_delay(2500, 4500)
        return post_result(True)
    except Exception as exc:
        logger.exception("Instagram posting failed.")
        shot = await poster.screenshot_failure("instagram_post_error")
        return post_result(False, error=f"{exc}; screenshot={shot}")
    finally:
        await poster.close()
