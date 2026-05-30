#!/usr/bin/env python3
"""Vercel build step: compile review-ui and stage static assets for CDN."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review-ui"
PUBLIC_STATIC = ROOT / "public" / "static"


def _stage_static_assets() -> None:
    """Vercel serves /public via CDN; Flask static_folder is unreliable on serverless."""
    src = ROOT / "web_ui" / "static"
    if not src.exists():
        return
    if PUBLIC_STATIC.exists():
        shutil.rmtree(PUBLIC_STATIC)
    shutil.copytree(src, PUBLIC_STATIC)
    print("Copied web_ui/static -> public/static")


def main() -> None:
    _stage_static_assets()
    if not (REVIEW / "package.json").exists():
        print("review-ui missing — skip frontend build")
        return
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    # Use npm install instead of npm ci to avoid lock file version mismatch
    # between npm v10 (Railway) and npm v11 (local dev).
    # Skip install entirely if node_modules already exists (nixpacks install phase ran it).
    if not (REVIEW / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=REVIEW, check=True)
    subprocess.run([npm, "run", "build"], cwd=REVIEW, check=True)
    dist = REVIEW / "dist" / "index.html"
    if not dist.exists():
        print("review-ui build failed: dist/index.html not found", file=sys.stderr)
        sys.exit(1)
    print("review-ui build OK")


if __name__ == "__main__":
    main()
