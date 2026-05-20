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
  (
    cd "$dir"
    exec bash -lc "$command"
  ) >"$log_file" 2>&1 &
  echo "$!" >"$pid_file"
  echo "[ok] $name started (pid $(cat "$pid_file"), log $log_file)"
}

start_backend() {
  local log_file="$LOG_DIR/backend.log"
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
  if ! command -v curl >/dev/null 2>&1; then
    echo "[?] $label $url (curl not installed)"
    return 0
  fi
  if curl --fail --silent --max-time 2 "$url" >/dev/null; then
    echo "[ok] $label $url"
  else
    echo "[X] $label $url"
    return 1
  fi
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
  check_repos
  start_backend
  start_background "engine" "$ENGINE_REPO" "exec make dev"
  start_background "site" "$SITE_REPO" "exec npm run dev -- --host 127.0.0.1 --port '$SITE_PORT'"
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
  if compgen -G "$LOG_DIR/*.log" >/dev/null; then
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
