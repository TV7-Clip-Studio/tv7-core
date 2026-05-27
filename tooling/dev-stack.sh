#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
DEV_STATE_DIR="${DEV_STATE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docs/.tmp/dev-stack}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
ENGINE_PORT="${ENGINE_PORT:-7070}"
SITE_PORT="${SITE_PORT:-4321}"

BACKEND_REPO="$REPO_ROOT/tv7-fastapi-backend"
ENGINE_REPO="$REPO_ROOT/tv7-axum-engine"
SITE_REPO="$REPO_ROOT/tv7-astro-site"
STUDIO_REPO="$REPO_ROOT/tv7-flutter-studio"

LOG_DIR="$DEV_STATE_DIR/logs"
PID_DIR="$DEV_STATE_DIR/pids"

usage() {
  cat <<EOF
Usage: dev-stack.sh {up|status|stop|logs}

Environment:
  REPO_ROOT       Workspace root containing the TV7 repos. Default: $REPO_ROOT
  DEV_STATE_DIR  Runtime logs and pid files. Default: $DEV_STATE_DIR
  BACKEND_PORT   Backend API port. Default: $BACKEND_PORT
  ENGINE_PORT    Axum engine port. Default: $ENGINE_PORT
  SITE_PORT      Astro site port. Default: $SITE_PORT
EOF
}

ensure_dirs() {
  mkdir -p "$LOG_DIR" "$PID_DIR"
}

has_makefile_target() {
  local repo_path="$1"
  local target="$2"
  if [[ ! -f "$repo_path/Makefile" ]]; then
    return 1
  fi
  grep -q "^${target}:" "$repo_path/Makefile"
}

repo_exists() {
  local name="$1"
  local path="$2"
  if [[ ! -d "$path" ]]; then
    echo "[X] $name missing at $path"
    return 1
  fi
  echo "[ok] $name at $path"
}

check_repos() {
  local ok=0
  repo_exists "backend" "$BACKEND_REPO" || ok=1
  repo_exists "engine" "$ENGINE_REPO" || ok=1
  repo_exists "site" "$SITE_REPO" || ok=1
  repo_exists "studio" "$STUDIO_REPO" || ok=1
  return "$ok"
}

pid_alive() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

start_background() {
  local name="$1"
  local dir="$2"
  local command="$3"
  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  if pid_alive "$pid_file"; then
    echo "[ok] $name already running (pid $(cat "$pid_file"))"
    return 0
  fi

  echo "[..] starting $name"
  # Note: Caller commands are prefixed with 'exec' (e.g., 'exec make dev') so that the actual
  # command process replaces the wrapper bash shell. This ensures the PID we record ($!) is
  # the target process itself, so killing the PID later terminates the server rather than leaving an orphan.
  (
    cd "$dir"
    bash -lc "$command"
  ) >"$log_file" 2>&1 &
  local pid=$!
  echo "$pid" >"$pid_file"
  
  # Liveness monitor: Sleep 0.5s on each check and verify the PID remains active.
  # This ensures any immediate startup failure (e.g. port already in use or command error)
  # is caught and reported to the developer, rather than falsely declaring success.
  local verified=1
  for ((attempt=1; attempt<=3; attempt++)); do
    sleep 0.5
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      verified=0
      break
    fi
  done

  if [[ "$verified" -eq 1 ]]; then
    echo "[ok] $name started (pid $pid, log $log_file)"
  else
    echo "[X] $name failed to start! See logs at $log_file"
    rm -f "$pid_file"
    return 1
  fi
}

start_backend() {
  local log_file="$LOG_DIR/backend.log"
  if ! has_makefile_target "$BACKEND_REPO" "up"; then
    echo "[X] backend Makefile or target 'up' missing at $BACKEND_REPO"
    return 1
  fi
  echo "[..] starting backend api/postgres with docker compose"
  (
    cd "$BACKEND_REPO"
    make up DETACH=1
  ) >"$log_file" 2>&1
  echo "[ok] backend compose requested (log $log_file)"
}

health_url() {
  local label="$1"
  local url="$2"
  local max_retries="${3:-1}"
  local delay="${4:-1}"
  
  if ! command -v curl >/dev/null 2>&1; then
    echo "[?] $label $url (curl not installed)"
    return 0
  fi
  
  for ((i=1; i<=max_retries; i++)); do
    if curl --fail --silent --max-time 2 "$url" >/dev/null; then
      echo "[ok] $label $url"
      return 0
    fi
    if ((i < max_retries)); then
      sleep "$delay"
    fi
  done
  
  echo "[X] $label $url"
  return 1
}

process_status() {
  local name="$1"
  local pid_file="$PID_DIR/$name.pid"
  if pid_alive "$pid_file"; then
    echo "[ok] $name process pid $(cat "$pid_file")"
  else
    echo "[X] $name process not running"
    return 1
  fi
}

up() {
  ensure_dirs
  check_repos || { echo "[X] Aborting: Missing required repos"; exit 1; }
  
  if ! has_makefile_target "$ENGINE_REPO" "dev"; then
    echo "[X] engine Makefile or target 'dev' missing at $ENGINE_REPO"
    return 1
  fi
  if [[ ! -f "$SITE_REPO/package.json" ]]; then
    echo "[X] site package.json missing at $SITE_REPO"
    return 1
  fi
  
  if ! start_backend; then
    echo "[X] Aborting: backend/Postgres failed to start. See $LOG_DIR/backend.log"
    return 1
  fi
  start_background "engine" "$ENGINE_REPO" "exec make dev"
  start_background "site" "$SITE_REPO" "exec npm run dev -- --host 127.0.0.1 --port '$SITE_PORT'"
  
  echo
  echo "Verifying service startup..."
  health_url "backend" "http://localhost:$BACKEND_PORT/health" 5 1 || true
  health_url "engine" "http://127.0.0.1:$ENGINE_PORT/health" 5 1 || true
  health_url "site" "http://localhost:$SITE_PORT/" 5 1 || true
  
  echo
  echo "TV7 dev stack requested."
  echo "Backend: http://localhost:$BACKEND_PORT/health"
  echo "Engine:  http://127.0.0.1:$ENGINE_PORT/health"
  echo "Site:    http://localhost:$SITE_PORT/"
  echo "Studio:  run 'make dev-studio' in tv7-core when you want Flutter desktop."
  echo "Logs:    $LOG_DIR"
}

status() {
  ensure_dirs
  echo "Repos:"
  check_repos || true
  echo
  echo "Processes:"
  process_status "engine" || true
  process_status "site" || true
  echo
  echo "Health:"
  health_url "backend" "http://localhost:$BACKEND_PORT/health" || true
  health_url "engine" "http://127.0.0.1:$ENGINE_PORT/health" || true
  health_url "site" "http://localhost:$SITE_PORT/" || true
  echo
  echo "Logs: $LOG_DIR"
}

stop_pid() {
  local name="$1"
  local pid_file="$PID_DIR/$name.pid"
  if pid_alive "$pid_file"; then
    local pid
    pid="$(cat "$pid_file")"
    echo "[..] stopping $name pid $pid"
    kill "$pid" >/dev/null 2>&1 || true
    rm -f "$pid_file"
    echo "[ok] $name stopped"
  else
    rm -f "$pid_file"
    echo "[ok] $name not running"
  fi
}

stop() {
  ensure_dirs
  stop_pid "site"
  stop_pid "engine"
  if [[ -d "$BACKEND_REPO" ]]; then
    echo "[..] stopping backend compose"
    (
      cd "$BACKEND_REPO"
      make down
    ) >"$LOG_DIR/backend-stop.log" 2>&1 || {
      echo "[X] backend compose stop failed (log $LOG_DIR/backend-stop.log)"
      return 1
    }
    echo "[ok] backend compose stopped"
  fi
}

logs() {
  ensure_dirs
  local files
  files=("$LOG_DIR"/*.log)
  if [[ -f "${files[0]}" ]]; then
    tail -n 80 "$LOG_DIR"/*.log
  else
    echo "No dev-stack logs yet at $LOG_DIR"
  fi
}

command="${1:-}"
case "$command" in
  up) up ;;
  status) status ;;
  stop) stop ;;
  logs) logs ;;
  -h|--help|help) usage ;;
  *)
    usage
    exit 2
    ;;
esac
