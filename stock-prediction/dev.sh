#!/usr/bin/env bash
# dev.sh — Start/stop both backend + frontend for local development
# Usage:
#   ./dev.sh start
#   ./dev.sh stop
#   ./dev.sh status
#   ./dev.sh logs
#   ./dev.sh restart

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

mkdir -p "$RUN_DIR"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

read_pid() {
  local file="$1"
  [[ -f "$file" ]] && cat "$file" || true
}

port_in_use() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

kill_port_listeners() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Freeing port $port (killing: $pids) …"
    # shellcheck disable=SC2086
    kill $pids >/dev/null 2>&1 || true
    sleep 0.5
    # If still listening, force kill.
    if port_in_use "$port"; then
      pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
      if [[ -n "$pids" ]]; then
        echo "Force killing port $port listeners: $pids …"
        # shellcheck disable=SC2086
        kill -9 $pids >/dev/null 2>&1 || true
      fi
    fi
  fi
}

wait_for_port_release() {
  local port="$1"
  local retries="${2:-10}"
  local i=0
  while port_in_use "$port"; do
    if [[ "$i" -ge "$retries" ]]; then
      return 1
    fi
    sleep 0.3
    i=$((i + 1))
  done
  return 0
}

venv_python() {
  if [[ -x "$BACKEND_DIR/.venv311/bin/python" ]]; then
    echo "$BACKEND_DIR/.venv311/bin/python"
  elif [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    echo "$BACKEND_DIR/.venv/bin/python"
  elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    echo "$ROOT_DIR/.venv/bin/python"
  else
    echo ""
  fi
}

start_backend() {
  local py
  py="$(venv_python)"
  [[ -n "$py" ]] || die "No backend venv found. Expected backend/.venv311 or backend/.venv."

  local pid
  pid="$(read_pid "$BACKEND_PID_FILE")"
  if is_pid_running "$pid"; then
    echo "Backend already running (pid=$pid)"
    return 0
  fi

  if port_in_use "$BACKEND_PORT"; then
    if [[ "${FORCE:-0}" == "1" ]]; then
      kill_port_listeners "$BACKEND_PORT"
      wait_for_port_release "$BACKEND_PORT" 15 || true
    fi
  fi
  if port_in_use "$BACKEND_PORT"; then
    die "Port $BACKEND_PORT already in use. Try: ./dev.sh restart --force (or change BACKEND_PORT)."
  fi

  : > "$BACKEND_LOG"
  echo "Starting backend on :$BACKEND_PORT …"
  (
    cd "$BACKEND_DIR"
    # Watch the whole stock-prediction folder so changes under model/ reload.
    "$py" -m uvicorn main:app \
      --reload \
      --host 0.0.0.0 \
      --port "$BACKEND_PORT" \
      --reload-dir "$ROOT_DIR" \
      2>&1 | tee -a "$BACKEND_LOG" &
    echo $! > "$BACKEND_PID_FILE"
  )
}

start_frontend() {
  if ! have_cmd node || ! have_cmd npm; then
    die "node/npm not found. Install Node.js (or use 'brew install node')."
  fi

  local pid
  pid="$(read_pid "$FRONTEND_PID_FILE")"
  if is_pid_running "$pid"; then
    echo "Frontend already running (pid=$pid)"
    return 0
  fi

  if port_in_use "$FRONTEND_PORT"; then
    if [[ "${FORCE:-0}" == "1" ]]; then
      kill_port_listeners "$FRONTEND_PORT"
      wait_for_port_release "$FRONTEND_PORT" 15 || true
    fi
  fi
  if port_in_use "$FRONTEND_PORT"; then
    die "Port $FRONTEND_PORT already in use. Try: ./dev.sh restart --force (or change FRONTEND_PORT)."
  fi

  : > "$FRONTEND_LOG"
  echo "Starting frontend on :$FRONTEND_PORT …"
  (
    cd "$FRONTEND_DIR"
    npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" >> "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )
}

stop_backend() {
  local pid
  pid="$(read_pid "$BACKEND_PID_FILE")"
  if is_pid_running "$pid"; then
    echo "Stopping backend (pid=$pid) …"
    kill "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$BACKEND_PID_FILE"
}

stop_frontend() {
  local pid
  pid="$(read_pid "$FRONTEND_PID_FILE")"
  if is_pid_running "$pid"; then
    echo "Stopping frontend (pid=$pid) …"
    kill "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$FRONTEND_PID_FILE"
}

status() {
  local bpid fpid
  bpid="$(read_pid "$BACKEND_PID_FILE")"
  fpid="$(read_pid "$FRONTEND_PID_FILE")"

  if is_pid_running "$bpid"; then
    echo "Backend:  RUNNING (pid=$bpid)  http://127.0.0.1:$BACKEND_PORT"
  else
    echo "Backend:  STOPPED"
  fi

  if is_pid_running "$fpid"; then
    echo "Frontend: RUNNING (pid=$fpid)  http://127.0.0.1:$FRONTEND_PORT"
  else
    echo "Frontend: STOPPED"
  fi

  echo "Logs: $RUN_DIR"
}

logs() {
  echo "Tailing logs (Ctrl+C to stop)…"
  echo "- $BACKEND_LOG"
  echo "- $FRONTEND_LOG"
  tail -n 200 -f "$BACKEND_LOG" "$FRONTEND_LOG"
}

cmd="${1:-start}"
arg2="${2:-}"
FORCE=0
if [[ "$arg2" == "--force" || "$arg2" == "-f" ]]; then
  FORCE=1
fi
case "$cmd" in
  start)
    start_backend
    start_frontend
    status
    ;;
  stop)
    stop_frontend
    stop_backend
    status
    ;;
  restart)
    stop_frontend
    stop_backend
    start_backend
    start_frontend
    status
    ;;
  status)
    status
    ;;
  logs)
    logs
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs} [--force]"
    exit 2
    ;;
esac
