#!/usr/bin/env sh
set -eu

if [ -x /opt/venv/bin/python ]; then
  export PATH="/opt/venv/bin:${PATH}"
fi

export PORT="${PORT:-8080}"
export DATABASE_PATH="${DATABASE_PATH:-/tmp/agent.db}"
export SOCIAL_AGENT_BACKGROUND_SCHEDULER="${SOCIAL_AGENT_BACKGROUND_SCHEDULER:-false}"
export TELEGRAM_POLLING_ENABLED="${TELEGRAM_POLLING_ENABLED:-false}"
export RAILWAY_FALLBACK_PORTS="${RAILWAY_FALLBACK_PORTS:-3000 5000 5001}"

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

set -- --bind "0.0.0.0:${PORT}" \
  --worker-class gthread \
  --workers 1 \
  --threads 8 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -

# Fallback ports disabled to ensure single binding for health checks.
# for fallback_port in ${RAILWAY_FALLBACK_PORTS}; do
#   if [ "${fallback_port}" != "${PORT}" ]; then
#     echo "Adding fallback web listener on 0.0.0.0:${fallback_port}"
#     set -- "$@" --bind "0.0.0.0:${fallback_port}"
#   fi
# done

exec "${GUNICORN}" "$@" web_ui.app:app --log-level debug
