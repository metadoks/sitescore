#!/bin/sh
set -eu

: "${PORT:?PORT is required}"

case "$PORT" in
  ''|*[!0-9]*) echo "PORT must be numeric" >&2; exit 64 ;;
esac

exec python -m uvicorn sitescore_api.app:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers 1
