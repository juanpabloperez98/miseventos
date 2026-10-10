#!/bin/sh
set -eu

FLASK_APP_FACTORY="app.bootstrap:create_app"

python - <<'PY'
import sys

from app.infrastructure.config import ConfigurationError, load_settings

try:
    load_settings()
except ConfigurationError as error:
    print(f"Invalid configuration: {error}", file=sys.stderr)
    sys.exit(1)
PY

alembic upgrade head

if [ "${FLASK_ENV:-development}" = "production" ]; then
  echo "FLASK_ENV=production: skipping seed-initial-data"
  exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-30}" \
    --preload \
    --access-logfile - \
    "${FLASK_APP_FACTORY}()"
fi

flask --app "${FLASK_APP_FACTORY}" seed-initial-data
exec flask --app "${FLASK_APP_FACTORY}" run --host 0.0.0.0 --port 5000 --debug
