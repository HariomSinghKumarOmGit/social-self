#!/usr/bin/env python3
"""Launch Chrome with remote debugging enabled for the Social Agent.

Usage:
    python -m sessions.launch_chrome          # Launch Chrome on port 9222
    python -m sessions.launch_chrome --port 9333  # Custom port

After Chrome is running, the agent connects to it automatically.
Your existing tabs, bookmarks, logins — everything stays as-is.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from sessions.browser_bridge import _find_chrome, DEFAULT_CDP_URL


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Chrome with debugging port")
    parser.add_argument("--port", type=int, default=9222, help="Debug port (default: 9222)")
    args = parser.parse_args()

    chrome_path = _find_chrome()
    if not chrome_path:
        print("❌ Chrome not found! Please start Chrome manually with:")
        print(f'   "/path/to/chrome" --remote-debugging-port={args.port}')
        sys.exit(1)

    print()
    print("=" * 60)
    print("  🌐  Social Agent — Chrome Launcher")
    print("=" * 60)
    print()
    print(f"  Chrome: {chrome_path}")
    print(f"  Debug port: {args.port}")
    print(f"  CDP endpoint: http://127.0.0.1:{args.port}")
    print()
    print("  ⚠️  IMPORTANT: Close ALL Chrome windows first!")
    print("  Chrome needs to restart with the debug flag.")
    print()

    confirm = input("  Ready? Press ENTER to launch Chrome (or Ctrl+C to cancel)... ")

    cmd = [chrome_path, f"--remote-debugging-port={args.port}"]
    print(f"\n  🚀 Launching Chrome...")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    if proc.poll() is None:
        print(f"  ✅ Chrome is running with debugging on port {args.port}")
        print()
        print("  You can now run the agent:")
        print("    python main.py")
        print()
        print("  Or test the connection:")
        print("    python -m sessions.test_bridge")
        print()
        print("  Chrome PID:", proc.pid)
        print("  (Chrome will keep running after this script exits)")
    else:
        print("  ❌ Chrome failed to start. Is another instance running?")
        print("     Close all Chrome windows and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
