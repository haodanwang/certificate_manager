#!/usr/bin/env bash
set -euo pipefail

# CertMon app start/stop script for Linux (CentOS 7.9 etc.)
# Usage:
#   ./scripts/certmon.sh start|stop|restart|reload|status|tail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
PYTHON="${PYTHON:-/usr/bin/python3}"
GUNICORN_APP="${GUNICORN_APP:-certmon.web:create_app()}"
BIND="${BIND:-127.0.0.1:8000}"
WORKERS="${WORKERS:-2}"
TIMEOUT="${TIMEOUT:-60}"

LOG_DIR="$APP_ROOT/var/log"
RUN_DIR="$APP_ROOT/var/run"
PID_FILE="$RUN_DIR/gunicorn.pid"
ACCESS_LOG="$LOG_DIR/access.log"
ERROR_LOG="$LOG_DIR/error.log"

ensure_dirs() {
  mkdir -p "$LOG_DIR" "$RUN_DIR"
}

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start() {
  ensure_dirs
  if is_running; then
    echo "[certmon] already running (pid $(cat "$PID_FILE"))"
    return 0
  fi
  export PYTHONUNBUFFERED=1
  export PYTHONPATH="$APP_ROOT"
  echo "[certmon] starting with $PYTHON (bind=$BIND, workers=$WORKERS)" | tee -a "$ERROR_LOG"
  "$PYTHON" -m gunicorn "$GUNICORN_APP" \
    -b "$BIND" \
    --workers "$WORKERS" \
    --timeout "$TIMEOUT" \
    --pid "$PID_FILE" \
    --access-logfile "$ACCESS_LOG" \
    --error-logfile "$ERROR_LOG" \
    --daemon
  sleep 0.5
  if is_running; then
    echo "[certmon] started (pid $(cat "$PID_FILE"))"
  else
    echo "[certmon] failed to start, check $ERROR_LOG" >&2
    exit 1
  fi
}

stop() {
  if ! is_running; then
    echo "[certmon] not running"
    return 0
  fi
  local pid
  pid="$(cat "$PID_FILE")"
  echo "[certmon] stopping pid $pid"
  kill -TERM "$pid" 2>/dev/null || true
  for i in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "[certmon] stopped"
      return 0
    fi
    sleep 0.3
  done
  echo "[certmon] force killing pid $pid"
  kill -KILL "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
}

reload_() {
  if ! is_running; then
    echo "[certmon] not running; starting instead"
    start
    return 0
  fi
  local pid
  pid="$(cat "$PID_FILE")"
  echo "[certmon] reloading pid $pid (HUP)"
  kill -HUP "$pid"
}

status() {
  if is_running; then
    echo "[certmon] running (pid $(cat "$PID_FILE"))"
  else
    echo "[certmon] not running"
    return 1
  fi
}

tail_logs() {
  ensure_dirs
  touch "$ERROR_LOG" "$ACCESS_LOG"
  echo "[certmon] tailing logs (Ctrl+C to stop):"
  tail -n 200 -F "$ERROR_LOG" "$ACCESS_LOG"
}

usage() {
  cat <<USAGE
Usage: $(basename "$0") <start|stop|restart|reload|status|tail>

Env vars (optional):
  PYTHON=/usr/bin/python3
  BIND=127.0.0.1:8000
  WORKERS=2
  TIMEOUT=60
  GUNICORN_APP=certmon.web:create_app()
USAGE
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  reload) reload_ ;;
  status) status ;;
  tail) tail_logs ;;
  *) usage; exit 1 ;;
esac


