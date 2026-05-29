#!/usr/bin/env python3
"""Vercel build step: compile review-ui for /review."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review-ui"


def main() -> None:
    if not (REVIEW / "package.json").exists():
        print("review-ui missing — skip frontend build")
        return
    subprocess.run(["npm", "ci"], cwd=REVIEW, check=True)
    subprocess.run(["npm", "run", "build"], cwd=REVIEW, check=True)
    dist = REVIEW / "dist" / "index.html"
    if not dist.exists():
        print("review-ui build failed: dist/index.html not found", file=sys.stderr)
        sys.exit(1)
    print("review-ui build OK")


if __name__ == "__main__":
    main()
