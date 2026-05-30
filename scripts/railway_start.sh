#!/usr/bin/env sh
set -eu

export PORT="${PORT:-8080}"
export DATABASE_PATH="${DATABASE_PATH:-/tmp/agent.db}"
export SOCIAL_AGENT_BACKGROUND_SCHEDULER="${SOCIAL_AGENT_BACKGROUND_SCHEDULER:-false}"
export TELEGRAM_POLLING_ENABLED="${TELEGRAM_POLLING_ENABLED:-false}"
export RAILWAY_FALLBACK_PORTS="${RAILWAY_FALLBACK_PORTS:-3000}"

echo "Starting Social Agent web on 0.0.0.0:${PORT}"
echo "Database path: ${DATABASE_PATH}"
echo "Background scheduler: ${SOCIAL_AGENT_BACKGROUND_SCHEDULER}"
echo "Telegram polling: ${TELEGRAM_POLLING_ENABLED}"
echo "Fallback public ports: ${RAILWAY_FALLBACK_PORTS}"

if [ -x /opt/venv/bin/gunicorn ]; then
  GUNICORN=/opt/venv/bin/gunicorn
else
  GUNICORN=gunicorn
fi

for fallback_port in ${RAILWAY_FALLBACK_PORTS}; do
  if [ "${fallback_port}" != "${PORT}" ]; then
    echo "Starting fallback web listener on 0.0.0.0:${fallback_port}"
    "${GUNICORN}" app:app \
      --bind "0.0.0.0:${fallback_port}" \
      --workers 1 \
      --threads 4 \
      --timeout 120 \
      --access-logfile - \
      --error-logfile - &
  fi
done

exec "${GUNICORN}" app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers 1 \
  --threads 8 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
