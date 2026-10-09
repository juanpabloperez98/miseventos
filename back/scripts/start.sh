#!/bin/sh
# Container entrypoint: validate configuration, migrate, seed (development only) and start the
# HTTP server. Any failing step stops the container with a non-zero exit code.
set -eu

FLASK_APP_FACTORY="app.bootstrap:create_app"

# Fail fast, before touching the database, if the configuration is invalid (e.g. a weak
# JWT_SECRET_KEY or seeders enabled in production). Messages never include secret values.
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
  # Seeding is never run in production (the settings above already refuse SEED_*_ENABLED=true).
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
