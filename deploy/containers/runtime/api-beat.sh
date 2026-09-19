#!/bin/sh
set -eu

SCHEDULE_FILE="${CELERY_BEAT_SCHEDULE_FILE:-/tmp/sitescore-celerybeat-schedule}"
PID_FILE="${CELERY_BEAT_PID_FILE:-/tmp/sitescore-celerybeat.pid}"

case "$SCHEDULE_FILE" in /tmp/*) ;; *) echo "CELERY_BEAT_SCHEDULE_FILE must be under /tmp" >&2; exit 64 ;; esac
case "$PID_FILE" in /tmp/*) ;; *) echo "CELERY_BEAT_PID_FILE must be under /tmp" >&2; exit 64 ;; esac

exec celery -A sitescore_api.tasks:celery_app beat \
  --schedule "$SCHEDULE_FILE" \
  --pidfile "$PID_FILE"
