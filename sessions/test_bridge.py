#!/usr/bin/env python3
"""Quick test to verify Chrome bridge connection is working.

Usage:
    python -m sessions.test_bridge
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sessions.browser_bridge import BrowserBridge


async def main() -> None:
    print()
    print("🔍 Testing Chrome bridge connection...")
    print()

    bridge = BrowserBridge()
    try:
        await bridge.connect()
        print("✅ Connected to Chrome!")

        ctx = bridge._default_context()
        pages = ctx.pages
        print(f"📑 Found {len(pages)} open tab(s):")
        for i, page in enumerate(pages):
            title = await page.title()
            print(f"   {i + 1}. {title[:60] or '(untitled)'} — {page.url[:80]}")

        # Test opening a new tab
        print("\n🧪 Opening a test tab...")
        page = await bridge.new_tab("https://www.google.com")
        title = await page.title()
        print(f"   ✅ Opened: {title}")

        await asyncio.sleep(2)
        await bridge.close_tab(page)
        print("   ✅ Closed test tab")

        # Check login status for social platforms
        print("\n🔐 Checking login status...")
        checks = [
            ("Instagram", "https://www.instagram.com/", 'svg[aria-label="Home"]'),
            ("X/Twitter", "https://x.com/home", '[data-testid="SideNav_AccountSwitcher_Button"]'),
            ("YouTube", "https://studio.youtube.com/", '#avatar-btn'),
        ]

        for name, url, selector in checks:
            page = await bridge.new_tab(url)
            await asyncio.sleep(3)
            try:
                await page.locator(selector).first.wait_for(timeout=5_000)
                print(f"   ✅ {name}: Logged in")
            except Exception:
                print(f"   ❌ {name}: Not logged in (log in manually in Chrome)")
            await bridge.close_tab(page)
            await asyncio.sleep(1)

    except ConnectionError as exc:
        print(f"❌ {exc}")
        print()
        print("💡 Start Chrome with debugging enabled first:")
        print("   python -m sessions.launch_chrome")
    finally:
        await bridge.disconnect()

    print()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
