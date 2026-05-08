# Module: youtube_post | Purpose: Upload videos via user's real Chrome.
# Public API: post_to_youtube

from __future__ import annotations

import logging
from typing import Dict

from poster.browser_poster import BrowserPoster, post_result

logger = logging.getLogger(__name__)


async def post_to_youtube(video_path: str, title: str, description: str) -> Dict[str, str]:
    """Upload a video to YouTube Studio using user's logged-in Chrome."""
    poster = BrowserPoster(platform="youtube")
    try:
        await poster.start()
        page = await poster.open_tab("https://studio.youtube.com/")
        await poster.human_delay(2500, 4000)

        # Verify logged in
        logged_in = await poster.verify_logged_in(
            "https://studio.youtube.com/",
            'ytcp-button[id="create-icon"], #avatar-btn',
        )
        if not logged_in:
            return post_result(False, error="Not logged in to YouTube in Chrome")

        # Click Create > Upload videos
        await page.locator('ytcp-button[id="create-icon"]').click()
        await poster.human_delay()
        await page.get_by_text("Upload videos").click()
        await poster.human_delay()

        # Upload video file
        await page.locator('input[type="file"]').set_input_files(video_path)
        await poster.human_delay(2000, 4000)

        # Fill title
        title_box = page.locator('textarea#textbox').nth(0)
        await title_box.click()
        await title_box.fill("")
        await title_box.type(title, delay=35)
        await poster.human_delay()

        # Fill description
        desc_box = page.locator('textarea#textbox').nth(1)
        await desc_box.click()
        await desc_box.type(description, delay=20)
        await poster.human_delay()

        # Click Next 3 times (Details → Video Elements → Checks → Visibility)
        for _ in range(3):
            await page.get_by_role("button", name="Next").click()
            await poster.human_delay()

        # Set Public
        await page.get_by_label("Public").click()
        await poster.human_delay()

        # Publish
        await page.get_by_role("button", name="Publish").click()
        await poster.human_delay(2500, 4500)

        return post_result(True, post_url="https://studio.youtube.com/")
    except Exception as exc:
        logger.exception("YouTube posting failed.")
        shot = await poster.screenshot_failure("yt_post_error")
        return post_result(False, error=f"{exc}; screenshot={shot}")
    finally:
        await poster.close()
