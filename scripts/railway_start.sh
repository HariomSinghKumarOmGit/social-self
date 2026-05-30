#!/usr/bin/env sh
set -eu

export PORT="${PORT:-8080}"
export DATABASE_PATH="${DATABASE_PATH:-/tmp/agent.db}"
export SOCIAL_AGENT_BACKGROUND_SCHEDULER="${SOCIAL_AGENT_BACKGROUND_SCHEDULER:-false}"
export TELEGRAM_POLLING_ENABLED="${TELEGRAM_POLLING_ENABLED:-false}"

echo "Starting Social Agent web on 0.0.0.0:${PORT}"
echo "Database path: ${DATABASE_PATH}"
echo "Background scheduler: ${SOCIAL_AGENT_BACKGROUND_SCHEDULER}"
echo "Telegram polling: ${TELEGRAM_POLLING_ENABLED}"

if [ -x /opt/venv/bin/gunicorn ]; then
  exec /opt/venv/bin/gunicorn app:app \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --threads 8 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
fi

exec gunicorn app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers 1 \
  --threads 8 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
