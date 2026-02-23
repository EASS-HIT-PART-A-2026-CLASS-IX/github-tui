#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${OCTOLENS_ENV_FILE:-$ROOT_DIR/.env}"
BOOT_VALIDATE="${OCTOLENS_BOOT_VALIDATE:-1}"
BOOT_START_FRONTEND="${OCTOLENS_BOOT_START_FRONTEND:-1}"
BOOT_LAUNCH_TUI="${OCTOLENS_BOOT_LAUNCH_TUI:-1}"
BOOT_OPEN_BROWSER="${OCTOLENS_BOOT_OPEN_BROWSER:-1}"
FRONTEND_HOST="${OCTOLENS_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${OCTOLENS_FRONTEND_PORT:-5173}"
STATE_DIR="${OCTOLENS_STATE_DIR:-$ROOT_DIR/.octolens}"
FRONTEND_PID_FILE="$STATE_DIR/frontend.pid"
FRONTEND_LOG_FILE="$STATE_DIR/frontend.log"
FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"

log() {
  printf '[boot] %s\n' "$1"
}

fail() {
  printf '[boot] ERROR: %s\n' "$1" >&2
  exit "${2:-1}"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command '$1' is not installed or not on PATH." 50
  fi
}

load_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    log "Loading environment from $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  else
    fail "Environment file not found at $ENV_FILE." 51
  fi
}

is_process_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

frontend_ready() {
  curl -fsS --max-time 3 "http://${FRONTEND_HOST}:${FRONTEND_PORT}" >/dev/null 2>&1
}

wait_for_frontend() {
  for _ in $(seq 1 45); do
    if frontend_ready; then
      return 0
    fi
    sleep 1
  done
  fail "Frontend did not become ready at ${FRONTEND_URL}." 52
}

open_frontend_in_browser() {
  if [[ "$BOOT_OPEN_BROWSER" != "1" ]]; then
    return 0
  fi

  if command -v open >/dev/null 2>&1; then
    open "$FRONTEND_URL" >/dev/null 2>&1 || log "Could not auto-open browser; open ${FRONTEND_URL} manually."
    return 0
  fi

  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || log "Could not auto-open browser; open ${FRONTEND_URL} manually."
    return 0
  fi

  log "No browser opener command found; open ${FRONTEND_URL} manually."
}

start_frontend() {
  mkdir -p "$STATE_DIR"

  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    local existing_pid
    existing_pid="$(cat "$FRONTEND_PID_FILE" 2>/dev/null || true)"
    if is_process_running "$existing_pid"; then
      log "Frontend dev server already running (PID $existing_pid)."
      open_frontend_in_browser
      return 0
    fi
    rm -f "$FRONTEND_PID_FILE"
  fi

  log "Starting frontend dev server on ${FRONTEND_URL} ..."
  (
    cd frontend
    if [[ ! -d node_modules ]]; then
      log "Installing frontend dependencies (node_modules missing)."
      npm ci
    fi
    VITE_DEV_PROXY_TARGET="${VITE_DEV_PROXY_TARGET:-http://localhost:8000}" \
      nohup npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
      >"$FRONTEND_LOG_FILE" 2>&1 &
    echo "$!" >"$FRONTEND_PID_FILE"
  )

  wait_for_frontend
  log "Frontend is ready."
  open_frontend_in_browser
}

require_cmd docker
require_cmd curl
if [[ "$BOOT_VALIDATE" == "1" || "$BOOT_LAUNCH_TUI" == "1" ]]; then
  require_cmd uv
fi
if [[ "$BOOT_VALIDATE" == "1" || "$BOOT_START_FRONTEND" == "1" ]]; then
  require_cmd npm
fi
load_env_file

OCTOLENS_RAMP_VALIDATE="$BOOT_VALIDATE" scripts/ramp_up.sh

if [[ "$BOOT_START_FRONTEND" == "1" ]]; then
  start_frontend
fi

if [[ "$BOOT_LAUNCH_TUI" == "1" ]]; then
  log "Launching TUI. Press 'q' to exit."
  uv run python main.py "$@"
fi

log "System boot complete."
log "Backend: http://localhost:8000"
if [[ "$BOOT_START_FRONTEND" == "1" ]]; then
  log "Frontend: ${FRONTEND_URL} (logs: $FRONTEND_LOG_FILE)"
fi
log "Stop backend: docker compose down"
if [[ "$BOOT_START_FRONTEND" == "1" ]]; then
  log "Stop frontend: kill \$(cat $FRONTEND_PID_FILE)"
fi
