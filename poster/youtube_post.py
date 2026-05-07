# Module: youtube_post | Purpose: Upload videos through YouTube Studio Playwright flow.
# Public API: post_to_youtube

from __future__ import annotations

import logging
from typing import Dict

from poster.browser_poster import BrowserPoster, post_result

logger = logging.getLogger(__name__)


async def post_to_youtube(video_path: str, title: str, description: str) -> Dict[str, str]:
    """Upload a video to YouTube Studio and publish it using persistent session."""
    poster = BrowserPoster(platform="youtube", headless=False)
    try:
        await poster.start()
        await poster.ensure_login(
            base_url="https://studio.youtube.com/",
            logged_in_selector='ytcp-button[id="create-icon"]',
            login_help_text="Please complete YouTube login in the opened browser.",
        )
        assert poster.page is not None
        await poster.page.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        await poster.human_delay()

        await poster.page.locator('ytcp-button[id="create-icon"]').click()
        await poster.human_delay()
        await poster.page.get_by_text("Upload videos").click()
        await poster.human_delay()

        await poster.page.locator('input[type="file"]').set_input_files(video_path)
        await poster.human_delay(2000, 4000)

        title_box = poster.page.locator('textarea#textbox').nth(0)
        await title_box.click()
        await title_box.fill("")
        await title_box.type(title, delay=35)
        await poster.human_delay()

        desc_box = poster.page.locator('textarea#textbox').nth(1)
        await desc_box.click()
        await desc_box.type(description, delay=20)
        await poster.human_delay()

        for _ in range(3):
            await poster.page.get_by_role("button", name="Next").click()
            await poster.human_delay()

        public_radio = poster.page.get_by_label("Public")
        await public_radio.click()
        await poster.human_delay()
        await poster.page.get_by_role("button", name="Publish").click()
        await poster.human_delay(2500, 4500)
        return post_result(True, post_url="https://studio.youtube.com/")
    except Exception as exc:
        logger.exception("YouTube posting failed.")
        shot = await poster.screenshot_failure("youtube_post_error")
        return post_result(False, error=f"{exc}; screenshot={shot}")
    finally:
        await poster.close()
