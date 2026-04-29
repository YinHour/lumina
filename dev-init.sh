#!/bin/bash
# One-click local development startup for Lumina / Open Notebook.
# Prefers non-Docker local services and only cleans up processes started by this script.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

API_PORT="${API_PORT:-5055}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
WORKER_STARTUP_WAIT="${WORKER_STARTUP_WAIT:-2}"
API_STARTUP_TIMEOUT="${API_STARTUP_TIMEOUT:-45}"
START_LOCAL_SURREAL="${START_LOCAL_SURREAL:-auto}"
LOCAL_SURREAL_DATA_DIR="${LOCAL_SURREAL_DATA_DIR:-$ROOT_DIR/.dev-data/surreal}"
LOCAL_SURREAL_BINARY="${LOCAL_SURREAL_BINARY:-}"

API_PID=""
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
host = url.hostname or '127.0.0.1'
port = url.port or (443 if url.scheme == 'wss' else 80)
print(host)
print(port)
PY
}

check_tcp() {
  python3 - "$1" "$2" <<'PY'
import socket, sys
host = sys.argv[1]
port = int(sys.argv[2])
s = socket.socket()
s.settimeout(1)
try:
    s.connect((host, port))
    sys.exit(0)
except Exception:
    sys.exit(1)
finally:
    s.close()
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

wait_for_pid() {
  local pid="$1"
  local seconds="$2"
  local elapsed=0
  while (( elapsed < seconds )); do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      return 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 0
}

find_local_surreal() {
  local candidates=()
  if [[ -n "$LOCAL_SURREAL_BINARY" ]]; then
    candidates+=("$LOCAL_SURREAL_BINARY")
  fi
  candidates+=(
    "$HOME/Library/Caches/surrealdb/surreal_v2"
    "$(command -v surreal 2>/dev/null || true)"
  )

  local candidate version
  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" ]] || continue
    [[ -x "$candidate" ]] || continue
    version="$($candidate version 2>/dev/null || true)"
    if [[ "$version" == 2.* ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    log "🛑 Stopping background worker..."
    kill "$WORKER_PID" >/dev/null 2>&1 || true
    wait "$WORKER_PID" 2>/dev/null || true
  fi

  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    log "🛑 Stopping API backend..."
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" 2>/dev/null || true
  fi

  if [[ "$STARTED_SURREAL" -eq 1 ]] && [[ -n "$SURREAL_PID" ]] && kill -0 "$SURREAL_PID" >/dev/null 2>&1; then
    log "🛑 Stopping local SurrealDB..."
    kill "$SURREAL_PID" >/dev/null 2>&1 || true
    wait "$SURREAL_PID" 2>/dev/null || true
  fi

  exit "$exit_code"
}

trap cleanup EXIT INT TERM

load_env_file

SURREAL_URL="${SURREAL_URL:-ws://127.0.0.1:8000/rpc}"
SURREAL_ENDPOINT="$(parse_ws_url "$SURREAL_URL")"
SURREAL_HOST="$(printf '%s\n' "$SURREAL_ENDPOINT" | sed -n '1p')"
SURREAL_PORT="$(printf '%s\n' "$SURREAL_ENDPOINT" | sed -n '2p')"

log "=== Lumina Dev Startup (local, non-Docker) ==="
log "Root:      $ROOT_DIR"
log "Database:  $SURREAL_URL"
log "API:       http://127.0.0.1:$API_PORT"
log "Frontend:  http://127.0.0.1:$FRONTEND_PORT"
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
      if ! SURREAL_BIN="$(find_local_surreal)"; then
        fail "SurrealDB not reachable and no local SurrealDB v2 binary was found. Set LOCAL_SURREAL_BINARY or start SurrealDB manually."
      fi
      mkdir -p "$LOCAL_SURREAL_DATA_DIR"
      log "🚀 Starting local SurrealDB with $SURREAL_BIN"
      "$SURREAL_BIN" start --log info --user root --pass root "rocksdb:$LOCAL_SURREAL_DATA_DIR" >/tmp/lumina-surreal.log 2>&1 &
      SURREAL_PID=$!
      STARTED_SURREAL=1

      for _ in $(seq 1 20); do
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
        fail "Local SurrealDB did not become reachable at $SURREAL_HOST:$SURREAL_PORT"
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
(
  cd "$ROOT_DIR"
  API_PORT="$API_PORT" uv run --env-file .env run_api.py
) >/tmp/lumina-api.log 2>&1 &
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
(
  cd "$ROOT_DIR"
  uv run --env-file .env python3 scripts/worker_with_timeout.py --import-modules commands
) >/tmp/lumina-worker.log 2>&1 &
WORKER_PID=$!

sleep "$WORKER_STARTUP_WAIT"
if ! kill -0 "$WORKER_PID" >/dev/null 2>&1; then
  cat /tmp/lumina-worker.log >&2 || true
  fail "Background worker exited during startup"
fi
log "✅ Background worker started"

log "🌐 Starting Next.js frontend..."
log ""
log "✅ Development environment is ready"
log "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
log "  API:      http://127.0.0.1:$API_PORT"
log "  API Docs: http://127.0.0.1:$API_PORT/docs"
log ""
log "Press Ctrl+C to stop all services started by this script."

cd "$ROOT_DIR/frontend"
npm run dev -- --port "$FRONTEND_PORT"
