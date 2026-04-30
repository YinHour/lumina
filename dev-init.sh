#!/bin/bash
# One-click local development startup for Lumina / Open Notebook.
# Prefers non-Docker local services and only cleans up processes started by this script.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

API_PORT="${API_PORT:-5055}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
API_STARTUP_TIMEOUT="${API_STARTUP_TIMEOUT:-90}"
FRONTEND_STARTUP_TIMEOUT="${FRONTEND_STARTUP_TIMEOUT:-60}"
WORKER_STARTUP_TIMEOUT="${WORKER_STARTUP_TIMEOUT:-30}"
SURREAL_STARTUP_TIMEOUT="${SURREAL_STARTUP_TIMEOUT:-30}"
START_LOCAL_SURREAL="${START_LOCAL_SURREAL:-auto}"
LOCAL_SURREAL_DATA_DIR="${LOCAL_SURREAL_DATA_DIR:-$ROOT_DIR/.dev-data/surreal}"
LOCAL_SURREAL_BINARY="${LOCAL_SURREAL_BINARY:-}"
DEV_INIT_PID_FILE="${DEV_INIT_PID_FILE:-/tmp/lumina-dev.pid}"

API_PID=""
FRONTEND_PID=""
WORKER_PID=""
SURREAL_PID=""
STARTED_SURREAL=0

log() {
  printf '%s\n' "$1"
}

fail() {
  printf '❌ %s\n' "$1" >&2
  exit 1
}

load_env_file() {
  if [[ -f "$ROOT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.env"
    set +a
  else
    fail ".env not found at $ROOT_DIR/.env"
  fi
}

parse_ws_url() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlparse

url = urlparse(sys.argv[1])
host = url.hostname or "127.0.0.1"
port = url.port or (443 if url.scheme == "wss" else 80)
print(host)
print(port)
PY
}

check_tcp() {
  python3 - "$1" "$2" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket()
sock.settimeout(1)
try:
    sock.connect((host, port))
    sys.exit(0)
except Exception:
    sys.exit(1)
finally:
    sock.close()
PY
}

require_port_free() {
  local port="$1"
  local name="$2"
  if lsof -i :"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "$name port $port is already in use. Stop the existing process first."
  fi
}

wait_for_http() {
  local url="$1"
  local timeout="$2"
  local elapsed=0

  while (( elapsed < timeout )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

wait_for_log() {
  local file="$1"
  local pattern="$2"
  local timeout="$3"
  local elapsed=0

  while (( elapsed < timeout )); do
    if [[ -f "$file" ]] && grep -q "$pattern" "$file"; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

terminate_process_tree() {
  local pid="$1"
  local child

  if [[ -z "$pid" ]] || ! kill -0 "$pid" >/dev/null 2>&1; then
    return 0
  fi

  while IFS= read -r child; do
    terminate_process_tree "$child"
  done < <(pgrep -P "$pid" 2>/dev/null || true)

  kill "$pid" >/dev/null 2>&1 || true
  wait "$pid" 2>/dev/null || true
}

find_local_surreal() {
  local candidates=()
  if [[ -n "$LOCAL_SURREAL_BINARY" ]]; then
    candidates+=("$LOCAL_SURREAL_BINARY")
  fi
  candidates+=(
    "$HOME/Library/Caches/surrealdb/surreal_v3"
    "$(command -v surreal 2>/dev/null || true)"
  )

  local candidate version
  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" ]] || continue
    [[ -x "$candidate" ]] || continue
    version="$($candidate version 2>/dev/null || true)"
    if [[ "$version" == 3.0.* ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM HUP

  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    log "🛑 Stopping frontend..."
    terminate_process_tree "$FRONTEND_PID"
  fi

  if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    log "🛑 Stopping background worker..."
    terminate_process_tree "$WORKER_PID"
  fi

  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    log "🛑 Stopping API backend..."
    terminate_process_tree "$API_PID"
  fi

  if [[ "$STARTED_SURREAL" -eq 1 ]] && [[ -n "$SURREAL_PID" ]] && kill -0 "$SURREAL_PID" >/dev/null 2>&1; then
    log "🛑 Stopping local SurrealDB..."
    terminate_process_tree "$SURREAL_PID"
  fi

  if [[ -f "$DEV_INIT_PID_FILE" ]] && [[ "$(cat "$DEV_INIT_PID_FILE" 2>/dev/null || true)" == "$$" ]]; then
    rm -f "$DEV_INIT_PID_FILE"
  fi

  exit "$exit_code"
}

stop_running_dev_environment() {
  if [[ ! -f "$DEV_INIT_PID_FILE" ]]; then
    log "No Lumina dev environment PID file found at $DEV_INIT_PID_FILE"
    return 0
  fi

  local pid
  pid="$(cat "$DEV_INIT_PID_FILE")"
  if [[ -z "$pid" ]] || ! kill -0 "$pid" >/dev/null 2>&1; then
    rm -f "$DEV_INIT_PID_FILE"
    log "Removed stale Lumina dev environment PID file."
    return 0
  fi

  log "Stopping Lumina dev environment started by PID $pid..."
  terminate_process_tree "$pid"
  rm -f "$DEV_INIT_PID_FILE"
}

if [[ "${1:-}" == "stop" ]]; then
  stop_running_dev_environment
  exit 0
fi

trap cleanup EXIT INT TERM HUP
printf '%s\n' "$$" > "$DEV_INIT_PID_FILE"

load_env_file

WORKER_MAX_TASKS="${WORKER_MAX_TASKS:-${SURREAL_COMMANDS_MAX_TASKS:-5}}"
SURREAL_URL="${SURREAL_URL:-ws://127.0.0.1:8000/rpc}"
SURREAL_ENDPOINT="$(parse_ws_url "$SURREAL_URL")"
SURREAL_HOST="$(printf '%s\n' "$SURREAL_ENDPOINT" | sed -n '1p')"
SURREAL_PORT="$(printf '%s\n' "$SURREAL_ENDPOINT" | sed -n '2p')"

log "=== Lumina Dev Startup (local, non-Docker) ==="
log "Root:      $ROOT_DIR"
log "Database:  $SURREAL_URL"
log "API:       http://127.0.0.1:$API_PORT"
log "Frontend:  http://127.0.0.1:$FRONTEND_PORT"
log "Worker:    max $WORKER_MAX_TASKS task(s)"
log "Logs:      /tmp/lumina-{surreal,api,worker,frontend}.log"
log ""

require_port_free "$API_PORT" "API"
require_port_free "$FRONTEND_PORT" "Frontend"

if check_tcp "$SURREAL_HOST" "$SURREAL_PORT"; then
  log "✅ SurrealDB already reachable at $SURREAL_HOST:$SURREAL_PORT"
else
  case "$START_LOCAL_SURREAL" in
    0|false|no)
      fail "SurrealDB not reachable at $SURREAL_HOST:$SURREAL_PORT and START_LOCAL_SURREAL is disabled."
      ;;
    auto|1|true|yes)
      if [[ "$SURREAL_HOST" != "127.0.0.1" && "$SURREAL_HOST" != "localhost" && "$SURREAL_HOST" != "::1" ]]; then
        fail "SurrealDB host '$SURREAL_HOST' is not local. Set SURREAL_URL=ws://127.0.0.1:$SURREAL_PORT/rpc for local startup or start the remote database separately."
      fi
      if ! SURREAL_BIN="$(find_local_surreal)"; then
        fail "SurrealDB not reachable and no local SurrealDB 3.0.x binary was found. Set LOCAL_SURREAL_BINARY or upgrade your local surreal binary."
      fi
      mkdir -p "$LOCAL_SURREAL_DATA_DIR"
      log "🚀 Starting local SurrealDB with $SURREAL_BIN"
      : > /tmp/lumina-surreal.log
      "$SURREAL_BIN" start --log info --user root --pass root --bind "$SURREAL_HOST:$SURREAL_PORT" "rocksdb:$LOCAL_SURREAL_DATA_DIR" </dev/null >/tmp/lumina-surreal.log 2>&1 &
      SURREAL_PID=$!
      STARTED_SURREAL=1

      for _ in $(seq 1 "$SURREAL_STARTUP_TIMEOUT"); do
        if check_tcp "$SURREAL_HOST" "$SURREAL_PORT"; then
          break
        fi
        if ! kill -0 "$SURREAL_PID" >/dev/null 2>&1; then
          cat /tmp/lumina-surreal.log >&2 || true
          fail "Local SurrealDB exited during startup."
        fi
        sleep 1
      done

      if ! check_tcp "$SURREAL_HOST" "$SURREAL_PORT"; then
        cat /tmp/lumina-surreal.log >&2 || true
        fail "Local SurrealDB did not become reachable at $SURREAL_HOST:$SURREAL_PORT within ${SURREAL_STARTUP_TIMEOUT}s"
      fi
      log "✅ Local SurrealDB started"
      ;;
    *)
      fail "Unsupported START_LOCAL_SURREAL value: $START_LOCAL_SURREAL"
      ;;
  esac
fi

log "📦 Syncing Python dependencies..."
uv sync

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  log "📦 Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
else
  log "✅ Frontend dependencies already present"
fi

log "🔧 Starting API backend..."
: > /tmp/lumina-api.log
(
  cd "$ROOT_DIR"
  API_PORT="$API_PORT" uv run --env-file .env run_api.py
) </dev/null >/tmp/lumina-api.log 2>&1 &
API_PID=$!

if ! wait_for_http "http://127.0.0.1:$API_PORT/api/auth/status" "$API_STARTUP_TIMEOUT"; then
  cat /tmp/lumina-api.log >&2 || true
  fail "API backend did not become healthy within ${API_STARTUP_TIMEOUT}s"
fi
log "✅ API backend is healthy"

log "👤 Initializing admin user..."
(
  cd "$ROOT_DIR"
  uv run --env-file .env python3 scripts/init-admin.py --force
) || log "⚠️  Admin init script failed (user may already exist)"

log "⚙️ Starting background worker..."
: > /tmp/lumina-worker.log
(
  cd "$ROOT_DIR"
  uv run --env-file .env python3 scripts/worker_with_timeout.py --import-modules commands --max-tasks "$WORKER_MAX_TASKS"
) </dev/null >/tmp/lumina-worker.log 2>&1 &
WORKER_PID=$!

if ! wait_for_log /tmp/lumina-worker.log "Using .* registered commands" "$WORKER_STARTUP_TIMEOUT"; then
  if ! kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    cat /tmp/lumina-worker.log >&2 || true
    fail "Background worker exited during startup"
  fi
  cat /tmp/lumina-worker.log >&2 || true
  fail "Background worker did not become ready within ${WORKER_STARTUP_TIMEOUT}s"
fi
log "✅ Background worker started"

log "🌐 Starting Next.js frontend..."
: > /tmp/lumina-frontend.log
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --port "$FRONTEND_PORT"
) </dev/null >/tmp/lumina-frontend.log 2>&1 &
FRONTEND_PID=$!

if ! wait_for_http "http://127.0.0.1:$FRONTEND_PORT" "$FRONTEND_STARTUP_TIMEOUT"; then
  cat /tmp/lumina-frontend.log >&2 || true
  fail "Frontend did not become healthy within ${FRONTEND_STARTUP_TIMEOUT}s"
fi

log ""
log "✅ Development environment is ready"
log "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
log "  API:      http://127.0.0.1:$API_PORT"
log "  API Docs: http://127.0.0.1:$API_PORT/docs"
log ""
log "Press Ctrl+C to stop all services started by this script."

wait "$FRONTEND_PID"
