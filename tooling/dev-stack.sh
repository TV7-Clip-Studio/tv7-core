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
Usage: dev-stack.sh {up|backend|engine|site|studio|status|stop|logs}

Environment:
  REPO_ROOT       Workspace root containing the TV7 repos. Default: $REPO_ROOT
  DEV_STATE_DIR  Runtime logs and pid files. Default: $DEV_STATE_DIR
  BACKEND_PORT   Backend API port. Default: $BACKEND_PORT
  ENGINE_PORT    Axum engine port. Default: $ENGINE_PORT
  SITE_PORT      Astro site port. Default: $SITE_PORT
  FORCE          Set to 1 to stop unknown managed-port or Studio-like processes.
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

pid_command() {
  local pid="$1"
  ps -p "$pid" -o args= 2>/dev/null || true
}

require_lsof() {
  if command -v lsof >/dev/null 2>&1; then
    return 0
  fi
  echo "[X] Missing required command: lsof" >&2
  echo "    Install lsof or run this on a standard macOS/Linux dev environment." >&2
  return 1
}

pid_cwd() {
  local pid="$1"
  require_lsof || return 0
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n1 || true
}

port_pid() {
  local port="$1"
  require_lsof || return 0
  lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n1 || true
}

known_engine_pid() {
  local pid="$1"
  local args
  args="$(pid_command "$pid")"
  [[ "$args" == *"tv7-axum-engine"* || "$args" == *"engine-service"* ]]
}

known_site_pid() {
  local pid="$1"
  local args cwd
  args="$(pid_command "$pid")"
  cwd="$(pid_cwd "$pid")"
  [[ "$args" == *"tv7-astro-site"* || "$cwd" == "$SITE_REPO"* ]]
}

known_studio_pid() {
  local pid="$1"
  local args cwd
  args="$(pid_command "$pid")"
  cwd="$(pid_cwd "$pid")"
  [[ "$args" == *"forgotten_client"* || ( "$cwd" == "$STUDIO_REPO"* && "$args" == *"flutter"* ) ]]
}

unique_lines() {
  awk 'NF && !seen[$0]++'
}

stop_pid_value() {
  local label="$1"
  local pid="$2"
  if [[ -z "$pid" ]]; then
    return 0
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 0
  fi
  echo "[..] stopping $label pid $pid"
  kill "$pid" >/dev/null 2>&1 || true
  for _ in 1 2 3 4 5; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "[ok] $label stopped"
      return 0
    fi
    sleep 0.5
  done
  echo "[..] force stopping $label pid $pid"
  kill -9 "$pid" >/dev/null 2>&1 || true
  echo "[ok] $label stopped"
}

stop_known_port_owner() {
  local label="$1"
  local port="$2"
  local known_fn="$3"
  local pid
  pid="$(port_pid "$port")"
  if [[ -z "$pid" ]]; then
    return 0
  fi

  local args
  args="$(pid_command "$pid")"
  echo "[..] $label port $port is occupied by pid $pid"
  if "$known_fn" "$pid" || [[ "${FORCE:-0}" == "1" ]]; then
    # Development guardrail: re-check ownership immediately before kill to avoid
    # stopping a replacement process if the original listener exited meanwhile.
    if [[ "$(port_pid "$port")" != "$pid" ]]; then
      echo "[X] $label port $port owner changed before stop; retry the command."
      return 1
    fi
    stop_pid_value "$label port owner" "$pid"
  else
    echo "[X] Refusing to stop unknown process on port $port: $args"
    echo "    Re-run with FORCE=1 if this process should be replaced."
    return 1
  fi
}

start_background() {
  local name="$1"
  local dir="$2"
  local command="$3"
  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  echo "[..] starting $name"
  (
    cd "$dir"
    exec bash -lc "$command"
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

stop_backend() {
  ensure_dirs
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

follow_backend_logs() {
  cd "$BACKEND_REPO"
  exec make logs
}

follow_log() {
  local name="$1"
  local log_file="$LOG_DIR/$name.log"
  echo "[..] following $name logs from $log_file"
  touch "$log_file"
  exec tail -n 80 -f "$log_file"
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

url_ok() {
  local url="$1"
  command -v curl >/dev/null 2>&1 || return 1
  curl --fail --silent --max-time 2 "$url" >/dev/null
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

port_status() {
  local label="$1"
  local port="$2"
  local pid
  pid="$(port_pid "$port")"
  if [[ -z "$pid" ]]; then
    echo "[X] $label port $port not listening"
    return 1
  fi
  echo "[ok] $label port $port pid $pid - $(pid_command "$pid")"
}

studio_pids() {
  {
    pgrep -x forgotten_client 2>/dev/null || true
    pgrep -f "flutter_tools.snapshot run|flutter run|make .*run-desktop|make -C .*run-desktop" 2>/dev/null || true
  } | while read -r pid; do
    [[ -n "$pid" ]] || continue
    if known_studio_pid "$pid"; then
      echo "$pid"
    fi
  done | unique_lines
}

studio_status() {
  local pids pid app_pid runner_pid
  pids="$(studio_pids)"
  if [[ -z "$pids" ]]; then
    echo "[X] studio process not running"
    return 1
  fi

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    if [[ "$(pid_command "$pid")" == *"forgotten_client.app"* ]]; then
      app_pid="$pid"
    elif [[ -z "${runner_pid:-}" ]]; then
      runner_pid="$pid"
    fi
  done <<<"$pids"

  if [[ -n "${app_pid:-}" ]]; then
    echo "[ok] studio app pid $app_pid - $(pid_command "$app_pid")"
  fi
  if [[ -n "${runner_pid:-}" ]]; then
    echo "[ok] studio runner pid $runner_pid - $(pid_command "$runner_pid")"
  fi
}

print_next_steps() {
  local printed=0
  echo "Next:"
  if ! url_ok "http://localhost:$BACKEND_PORT/health"; then
    echo "- Backend down: run make dev-backend"
    printed=1
  fi
  if ! url_ok "http://127.0.0.1:$ENGINE_PORT/health"; then
    echo "- Engine down: run make dev-engine"
    printed=1
  fi
  if ! url_ok "http://localhost:$SITE_PORT/"; then
    echo "- Site down: run make dev-site"
    printed=1
  fi
  if ! studio_status >/dev/null 2>&1; then
    echo "- Studio down: run make dev-studio"
    printed=1
  fi
  if [[ "$printed" -eq 0 ]]; then
    echo "- All local services appear to be up."
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
  stop_engine
  stop_site
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
  studio_status || true
  echo
  echo "Ports:"
  port_status "backend" "$BACKEND_PORT" || true
  port_status "engine" "$ENGINE_PORT" || true
  port_status "site" "$SITE_PORT" || true
  echo
  echo "Health:"
  health_url "backend" "http://localhost:$BACKEND_PORT/health" || true
  health_url "engine" "http://127.0.0.1:$ENGINE_PORT/health" || true
  health_url "site" "http://localhost:$SITE_PORT/" || true
  echo
  echo "Logs: $LOG_DIR"
  echo
  print_next_steps
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

stop_engine() {
  ensure_dirs
  stop_pid "engine"
  stop_known_port_owner "engine" "$ENGINE_PORT" known_engine_pid
}

stop_site() {
  ensure_dirs
  stop_pid "site"
  stop_known_port_owner "site" "$SITE_PORT" known_site_pid
}

stop_studio() {
  ensure_dirs
  local pids pid
  pids="$(studio_pids)"
  if [[ -z "$pids" ]]; then
    echo "[ok] studio not running"
    return 0
  fi
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    if known_studio_pid "$pid" || [[ "${FORCE:-0}" == "1" ]]; then
      stop_pid_value "studio" "$pid"
    else
      echo "[X] Refusing to stop unknown studio-like process pid $pid: $(pid_command "$pid")"
      echo "    Re-run with FORCE=1 if this process should be replaced."
      return 1
    fi
  done <<<"$pids"
}

backend() {
  ensure_dirs
  repo_exists "backend" "$BACKEND_REPO"
  stop_backend
  start_backend
  follow_backend_logs
}

engine() {
  ensure_dirs
  repo_exists "engine" "$ENGINE_REPO"
  if ! has_makefile_target "$ENGINE_REPO" "dev"; then
    echo "[X] engine Makefile or target 'dev' missing at $ENGINE_REPO"
    return 1
  fi
  stop_engine
  echo "[..] starting engine in foreground"
  cd "$ENGINE_REPO"
  exec make dev
}

site() {
  ensure_dirs
  repo_exists "site" "$SITE_REPO"
  if [[ ! -f "$SITE_REPO/package.json" ]]; then
    echo "[X] site package.json missing at $SITE_REPO"
    return 1
  fi
  stop_site
  echo "[..] starting site in foreground"
  cd "$SITE_REPO"
  exec npm run dev -- --host 127.0.0.1 --port "$SITE_PORT"
}

studio() {
  ensure_dirs
  repo_exists "studio" "$STUDIO_REPO"
  stop_studio
  echo "[..] starting studio in foreground"
  cd "$STUDIO_REPO"
  exec make run-desktop
}

stop() {
  ensure_dirs
  stop_site
  stop_engine
  stop_backend
  if [[ "${INCLUDE_STUDIO:-0}" == "1" ]]; then
    stop_studio
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
  backend) backend ;;
  engine) engine ;;
  site) site ;;
  studio) studio ;;
  status) status ;;
  stop) stop ;;
  logs) logs ;;
  -h|--help|help) usage ;;
  *)
    usage
    exit 2
    ;;
esac
