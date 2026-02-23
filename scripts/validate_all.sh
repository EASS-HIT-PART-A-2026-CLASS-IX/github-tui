#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
ENV_FILE="${OCTOLENS_ENV_FILE:-$ROOT_DIR/.env}"

log() {
  printf '[validate_all] %s\n' "$1"
}

fail() {
  printf '[validate_all] ERROR: %s\n' "$1" >&2
  exit "${2:-1}"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command '$1' is not installed or not on PATH." 10
  fi
}

load_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    log "Loading environment from $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}

require_cmd uv
require_cmd npm
load_env_file

log "Gate A: Python tests (uv run pytest -q)"
uv run pytest -q

log "Gate B: Frontend lint + build"
(
  cd frontend
  if [[ ! -d node_modules ]]; then
    log "Installing frontend dependencies (node_modules missing)."
    npm ci
  fi
  npm run lint
  npm run build
)

log "Validation passed: tests + frontend checks are green."
