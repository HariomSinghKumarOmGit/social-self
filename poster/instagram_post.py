# Module: instagram_post | Purpose: Publish Instagram posts via user's real Chrome.
# Public API: post_to_instagram

from __future__ import annotations

import logging
from typing import Dict

from poster.browser_poster import BrowserPoster, post_result

logger = logging.getLogger(__name__)


async def post_to_instagram(image_path: str, caption: str) -> Dict[str, str]:
    """Upload an image post to Instagram using user's logged-in Chrome."""
    poster = BrowserPoster(platform="instagram")
    try:
        await poster.start()
        page = await poster.open_tab("https://www.instagram.com/")
        await poster.human_delay(2000, 3500)

        # Verify logged in
        logged_in = await poster.verify_logged_in(
            "https://www.instagram.com/",
            'svg[aria-label="Home"], svg[aria-label="Search"]',
        )
        if not logged_in:
            return post_result(False, error="Not logged in to Instagram in Chrome")

        # Click New Post button
        await page.locator('svg[aria-label="New post"], div[role="menuitem"]').first.click()
        await poster.human_delay()

        # Upload image
        await page.locator('input[type="file"]').set_input_files(image_path)
        await poster.human_delay(1500, 2500)

        # Click Next twice (crop → filter → caption)
        for _ in range(2):
            next_btn = page.get_by_role("button", name="Next")
            await next_btn.click()
            await poster.human_delay()

        # Type caption
        caption_box = page.locator('div[aria-label="Write a caption..."]').first
        await caption_box.click()
        await caption_box.type(caption, delay=40)
        await poster.human_delay()

        # Share
        await page.get_by_role("button", name="Share").click()
        await poster.human_delay(2500, 4500)

        return post_result(True)
    except Exception as exc:
        logger.exception("Instagram posting failed.")
        shot = await poster.screenshot_failure("ig_post_error")
        return post_result(False, error=f"{exc}; screenshot={shot}")
    finally:
        await poster.close()
