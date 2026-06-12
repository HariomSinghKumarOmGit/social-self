#!/usr/bin/env bash
# One-command local start: build review UI + run web + bot + scheduler
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PORT="${PORT:-56823}"
export TELEGRAM_POLLING_ENABLED="${TELEGRAM_POLLING_ENABLED:-true}"
export WEB_UI_PORT="$PORT"

echo "Building review UI…"
if [ -f review-ui/package.json ]; then
  (cd review-ui && npm ci && npm run build)
fi

echo ""
echo "Starting Social Agent at http://127.0.0.1:${PORT}"
echo "  Calendar: /"
echo "  Feed:     /feed"
echo "  Review:   /review"
echo ""

exec python3 main.py
