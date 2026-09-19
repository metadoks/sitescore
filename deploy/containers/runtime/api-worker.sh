#!/bin/sh
set -eu

CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-1}"
case "$CELERY_CONCURRENCY" in
  ''|*[!0-9]*) echo "CELERY_CONCURRENCY must be a positive integer" >&2; exit 64 ;;
esac
if [ "$CELERY_CONCURRENCY" -lt 1 ]; then
  echo "CELERY_CONCURRENCY must be at least 1" >&2
  exit 64
fi

exec celery -A sitescore_api.tasks:celery_app worker \
  --concurrency "$CELERY_CONCURRENCY"
