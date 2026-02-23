#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${OCTOLENS_ENV_FILE:-$ROOT_DIR/.env}"
BASE_URL="${OCTOLENS_BASE_URL:-http://localhost:8000}"
PRIMARY_USERNAME="${OCTOLENS_DEMO_USERNAME:-openai}"
FALLBACK_USERNAME="${OCTOLENS_FALLBACK_USERNAME:-octocat}"
RUN_VALIDATE="${OCTOLENS_RAMP_VALIDATE:-1}"
STRICT_AI_CHECKS="${OCTOLENS_RAMP_STRICT_AI:-0}"
COMPOSE_ATTEMPTS="${OCTOLENS_COMPOSE_ATTEMPTS:-3}"
COMPOSE_RETRY_WAIT_SECONDS="${OCTOLENS_COMPOSE_RETRY_WAIT_SECONDS:-5}"

log() {
  printf '[ramp_up] %s\n' "$1"
}

fail() {
  printf '[ramp_up] ERROR: %s\n' "$1" >&2
  exit "${2:-1}"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command '$1' is not installed or not on PATH." 40
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
    fail "Environment file not found at $ENV_FILE." 41
  fi
}

start_docker_stack() {
  local attempt=1
  while [[ "$attempt" -le "$COMPOSE_ATTEMPTS" ]]; do
    if docker compose up --build -d; then
      return 0
    fi

    if [[ "$attempt" -eq "$COMPOSE_ATTEMPTS" ]]; then
      break
    fi

    log "Docker startup failed (attempt ${attempt}/${COMPOSE_ATTEMPTS}); retrying in ${COMPOSE_RETRY_WAIT_SECONDS}s..."
    sleep "$COMPOSE_RETRY_WAIT_SECONDS"
    attempt=$((attempt + 1))
  done

  fail "Docker stack failed to start after ${COMPOSE_ATTEMPTS} attempts." 46
}

extract_body_from_raw() {
  local raw="$1"
  RAW_RESPONSE="$raw" python3 - <<'PY'
import os

raw = os.environ["RAW_RESPONSE"]
parts = raw.rsplit("\n", 1)
if len(parts) != 2:
    raise SystemExit("Could not parse HTTP status marker from curl output.")
print(parts[0])
PY
}

extract_status_from_raw() {
  local raw="$1"
  RAW_RESPONSE="$raw" python3 - <<'PY'
import os

raw = os.environ["RAW_RESPONSE"]
parts = raw.rsplit("\n", 1)
if len(parts) != 2:
    raise SystemExit("Could not parse HTTP status marker from curl output.")
status = parts[1].strip()
if not status.isdigit():
    raise SystemExit("HTTP status marker is not numeric.")
print(status)
PY
}

http_get_raw() {
  local path="$1"
  curl -sS --max-time 45 -w $'\n%{http_code}' "$BASE_URL$path"
}

assert_health_ok() {
  local raw status body
  raw="$(http_get_raw '/api/v1/health')"
  status="$(extract_status_from_raw "$raw")"
  body="$(extract_body_from_raw "$raw")"
  [[ "$status" == "200" ]] || fail "Health check failed with HTTP $status and body: $body" 42
  BODY_JSON="$body" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["BODY_JSON"])
if payload.get("status") != "ok":
    raise SystemExit(f"Unexpected health payload: {payload}")
PY
}

check_ai_ready() {
  local username="$1"
  local transport="$2"
  local raw status body
  if ! raw="$(http_get_raw "/api/v1/insights/${username}?transport=${transport}&llm=true" 2>/dev/null)"; then
    log "Insights check request failed for @${username} via ${transport}."
    return 1
  fi

  status="$(extract_status_from_raw "$raw")"
  body="$(extract_body_from_raw "$raw")"

  if [[ "$status" != "200" ]]; then
    log "Insights check failed for @${username} via ${transport} (HTTP $status)."
    return 1
  fi

  if ! BODY_JSON="$body" USERNAME="$username" TRANSPORT="$transport" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["BODY_JSON"])
username = os.environ["USERNAME"]
transport = os.environ["TRANSPORT"]

repos = payload.get("repositories")
if not isinstance(repos, list) or not repos:
    raise SystemExit(f"No repositories returned for @{username} via {transport}.")
ai = payload.get("ai_insights")
if not isinstance(ai, dict):
    raise SystemExit(f"Missing ai_insights block for @{username} via {transport}.")
if ai.get("status") != "ready":
    raise SystemExit(
        f"AI status is '{ai.get('status')}' for @{username} via {transport}. Expected 'ready'."
    )
if not (ai.get("summary") or "").strip():
    raise SystemExit(f"AI summary is empty for @{username} via {transport}.")
PY
  then
    log "Insights payload check failed for @${username} via ${transport}."
    return 1
  fi

  return 0
}

require_cmd docker
require_cmd curl
require_cmd python3

load_env_file

if [[ -z "${GROQ_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" && -z "${GEMINI_API_KEY:-}" ]]; then
  fail "Set GROQ_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY in $ENV_FILE." 44
fi

if ! docker info >/dev/null 2>&1; then
  fail "Docker daemon is not reachable. Start Docker Desktop / daemon and retry." 45
fi

if [[ "$RUN_VALIDATE" == "1" ]]; then
  log "Running validation gates before startup..."
  scripts/validate_all.sh
fi

log "Starting Docker stack..."
start_docker_stack

log "Waiting for API readiness at ${BASE_URL}/api/v1/health ..."
for _ in $(seq 1 30); do
  if raw="$(http_get_raw '/api/v1/health' 2>/dev/null)"; then
    status="$(extract_status_from_raw "$raw" || true)"
    if [[ "$status" == "200" ]]; then
      break
    fi
  fi
  sleep 1
done

assert_health_ok
log "Health check passed."

candidate_usernames=("$PRIMARY_USERNAME")
if [[ "$FALLBACK_USERNAME" != "$PRIMARY_USERNAME" ]]; then
  candidate_usernames+=("$FALLBACK_USERNAME")
fi

selected_username=""
for username in "${candidate_usernames[@]}"; do
  if check_ai_ready "$username" "httpx" && check_ai_ready "$username" "curl"; then
    selected_username="$username"
    break
  fi
  log "Username @${username} did not pass both transport checks; trying next candidate."
done

if [[ -z "$selected_username" ]]; then
  if [[ "$STRICT_AI_CHECKS" == "1" ]]; then
    fail "No username passed both transport checks with AI-ready output." 43
  fi
  log "No username passed both transport checks; continuing because OCTOLENS_RAMP_STRICT_AI=0."
  log "Tip: rerun later, set OCTOLENS_DEMO_USERNAME, or use OCTOLENS_RAMP_STRICT_AI=1 to fail fast."
else
  log "AI checks passed in httpx + curl modes for @${selected_username}."
fi

log "System is up."
log "Web UI: cd frontend && VITE_DEV_PROXY_TARGET=http://localhost:8000 npm run dev"
log "TUI: uv run python main.py"
log "Stop backend: docker compose down"
