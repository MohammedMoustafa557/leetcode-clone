#!/bin/sh
set -e
echo "Running database migrations..."
alembic upgrade head
if [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "Seeding problems (first start downloads ~100 MB of public data)..."
  python -m scripts.seed --if-empty
  echo "Downloading learning books (System Design Primer, system-design course, behavioral handbook)..."
  python -m scripts.fetch_docs --if-missing || echo "Book download failed; Learn > Books will be empty until it succeeds."
fi
exec "$@"
