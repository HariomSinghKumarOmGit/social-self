#!/usr/bin/env python3
"""Interactive CLI to set up Playwright login sessions for each platform.

Usage:
    python -m sessions.login_setup                # Login to ALL platforms
    python -m sessions.login_setup instagram      # Login to Instagram only
    python -m sessions.login_setup twitter youtube # Login to specific platforms
    python -m sessions.login_setup --check         # Check all session statuses
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sessions.session_manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║       🔐  Social Agent — Session Login Setup  🔐        ║
╠══════════════════════════════════════════════════════════╣
║  This tool opens a real browser for each platform.      ║
║  Log in manually, then press ENTER when done.           ║
║  Sessions are saved permanently until they expire.      ║
╚══════════════════════════════════════════════════════════╝
"""


async def check_sessions() -> None:
    """Print status of all platform sessions."""
    print("\n📋 Session Status Report\n" + "─" * 40)
    for platform in SessionManager.list_platforms():
        mgr = SessionManager(platform=platform, headless=True)
        meta = mgr.get_metadata()
        if meta:
            status = "✅ Saved" if meta.get("verified") else "⚠️  Unverified"
            last = meta.get("last_login", "unknown")
            print(f"  {platform:12s}  {status}  (last login: {last})")
        else:
            print(f"  {platform:12s}  ❌ No session found")

    # Also do a live check
    print("\n🔄 Live verification (opening headless browsers)...\n")
    for platform in SessionManager.list_platforms():
        mgr = SessionManager(platform=platform, headless=True)
        if not mgr.session_exists():
            print(f"  {platform:12s}  ⏭  Skipped (no session)")
            continue
        try:
            await mgr.start()
            logged_in = await mgr.is_logged_in()
            status = "✅ Valid" if logged_in else "❌ Expired"
            print(f"  {platform:12s}  {status}")
        except Exception as exc:
            print(f"  {platform:12s}  ❌ Error: {exc}")
        finally:
            await mgr.close()
    print()


async def login_platform(platform: str) -> bool:
    """Run interactive login for one platform."""
    print(f"\n{'─' * 50}")
    print(f"  🌐 Setting up: {platform.upper()}")
    print(f"{'─' * 50}")

    mgr = SessionManager(platform=platform, headless=False)
    try:
        await mgr.start()

        # Check if already logged in
        if mgr.session_exists():
            print(f"  ℹ️  Existing session found for {platform}. Checking validity...")
            if await mgr.is_logged_in():
                print(f"  ✅ {platform.title()} session is still valid! Skipping login.")
                relogin = input("  Want to re-login anyway? [y/N]: ").strip().lower()
                if relogin != "y":
                    return True

        success = await mgr.interactive_login()
        return success
    except Exception as exc:
        print(f"\n  ❌ Error during {platform} setup: {exc}")
        return False
    finally:
        await mgr.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Set up Playwright login sessions")
    parser.add_argument(
        "platforms",
        nargs="*",
        choices=SessionManager.list_platforms() + [[]],
        default=[],
        help="Platforms to log in to (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check current session statuses",
    )
    args = parser.parse_args()

    print(BANNER)

    if args.check:
        await check_sessions()
        return

    platforms = args.platforms if args.platforms else SessionManager.list_platforms()

    results = {}
    for platform in platforms:
        results[platform] = await login_platform(platform)

    # Summary
    print("\n" + "═" * 50)
    print("  📊 Setup Summary")
    print("═" * 50)
    for platform, success in results.items():
        icon = "✅" if success else "❌"
        print(f"  {icon}  {platform.title()}")
    print()

    failed = [p for p, s in results.items() if not s]
    if failed:
        print(f"  ⚠️  Re-run for failed platforms: python -m sessions.login_setup {' '.join(failed)}")
    else:
        print("  🎉 All sessions saved! You're ready to auto-post.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
