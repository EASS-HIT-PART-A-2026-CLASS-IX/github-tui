#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
ENV_FILE="${OCTOLENS_ENV_FILE:-$ROOT_DIR/.env}"

BASE_URL="${OCTOLENS_BASE_URL:-http://localhost:8000}"
USERNAME_CANDIDATES=("openai" "octocat")
INVALID_USERNAME="__octolens_missing_user_404_check__"

log() {
  printf '[demo_check] %s\n' "$1"
}

fail() {
  printf '[demo_check] ERROR: %s\n' "$1" >&2
  exit "${2:-1}"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command '$1' is not installed or not on PATH." 20
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

cleanup() {
  if [[ "${STARTED_COMPOSE:-0}" == "1" ]]; then
    log "Stopping Docker Compose stack..."
    docker compose down >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

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
  [[ "$status" == "200" ]] || fail "Health check failed with HTTP $status and body: $body" 30
  BODY_JSON="$body" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["BODY_JSON"])
if payload.get("status") != "ok":
    raise SystemExit(f"Unexpected health payload: {payload}")
PY
  log "Health check passed."
}

assert_insights_payload() {
  local body="$1"
  local transport="$2"
  local username="$3"
  BODY_JSON="$body" TRANSPORT="$transport" USERNAME="$username" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["BODY_JSON"])
transport = os.environ["TRANSPORT"]
username = os.environ["USERNAME"]

if not isinstance(payload.get("repositories"), list) or len(payload["repositories"]) == 0:
    raise SystemExit(f"No repositories returned for @{username} via {transport}.")
metrics = payload.get("metrics")
if not isinstance(metrics, dict):
    raise SystemExit(f"Missing metrics block for @{username} via {transport}.")
for key in ("total_stars", "total_forks", "score"):
    if key not in metrics:
        raise SystemExit(f"Missing metrics.{key} for @{username} via {transport}.")
ai = payload.get("ai_insights")
if not isinstance(ai, dict):
    raise SystemExit(f"Missing ai_insights block for @{username} via {transport}.")
if ai.get("status") != "ready":
    raise SystemExit(
        f"AI status is '{ai.get('status')}' for @{username} via {transport}. "
        "Expected 'ready'."
    )
summary = (ai.get("summary") or "").strip()
if not summary:
    raise SystemExit(f"AI summary is empty for @{username} via {transport}.")
PY
}

check_transport_for_username() {
  local username="$1"
  local transport="$2"
  local path raw status body
  path="/api/v1/insights/${username}?transport=${transport}&llm=true"
  raw="$(http_get_raw "$path")"
  status="$(extract_status_from_raw "$raw")"
  body="$(extract_body_from_raw "$raw")"

  if [[ "$status" != "200" ]]; then
    return 1
  fi

  if ! assert_insights_payload "$body" "$transport" "$username"; then
    return 1
  fi

  log "Insights check passed for transport=${transport}, username=@${username}."
  return 0
}

assert_invalid_username_fails() {
  local path raw status body
  path="/api/v1/insights/${INVALID_USERNAME}?transport=httpx"
  raw="$(http_get_raw "$path")"
  status="$(extract_status_from_raw "$raw")"
  body="$(extract_body_from_raw "$raw")"

  if [[ "$status" == "200" ]]; then
    fail "Invalid username unexpectedly returned HTTP 200: $body" 31
  fi

  BODY_JSON="$body" HTTP_STATUS="$status" python3 - <<'PY'
import json
import os

status = int(os.environ["HTTP_STATUS"])
payload = json.loads(os.environ["BODY_JSON"])
if status != 404:
    raise SystemExit(f"Expected HTTP 404 for invalid username, got {status}: {payload}")
detail = payload.get("detail")
if not isinstance(detail, str) or not detail.strip():
    raise SystemExit(f"Missing error detail in invalid username response: {payload}")
PY

  log "Invalid-username check passed (HTTP 404 with detail)."
}

require_cmd docker
require_cmd curl
require_cmd python3
load_env_file

if [[ -z "${GROQ_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" && -z "${GEMINI_API_KEY:-}" ]]; then
  fail "Set GROQ_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY before running demo_check.sh." 21
fi

if ! docker info >/dev/null 2>&1; then
  fail "Docker daemon is not reachable. Start Docker Desktop / daemon and retry." 22
fi

log "Starting Docker Compose stack (build + detached)..."
STARTED_COMPOSE=1
docker compose up --build -d >/dev/null

log "Waiting for API health at ${BASE_URL}/api/v1/health ..."
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

selected_username=""
for username in "${USERNAME_CANDIDATES[@]}"; do
  if check_transport_for_username "$username" "httpx" && check_transport_for_username "$username" "curl"; then
    selected_username="$username"
    break
  fi
  log "Username @${username} did not pass both transport checks; trying next candidate."
done

if [[ -z "$selected_username" ]]; then
  fail "No candidate username passed both transport checks with AI ready output." 32
fi

log "Transport parity confirmed with username @${selected_username}."
assert_invalid_username_fails

log "Demo runtime checks passed."
log "This run validated: health, httpx+curl parity, AI-ready output, and invalid-username handling."
