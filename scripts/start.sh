#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pids=()
names=()

usage() {
  cat <<'USAGE'
Usage: ./scripts/start.sh

Start the local app:
  - FastAPI backend on http://localhost:8000
  - Next.js frontend on http://localhost:3000

The SQLite database and uploaded files live in backend/data/.

Options:
  -h, --help          Show this help.
USAGE
}

log() {
  printf '\n==> %s\n' "$1"
}

need_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

cleanup() {
  local status=$?
  trap - INT TERM EXIT

  if [[ ${#pids[@]} -gt 0 ]]; then
    log "Stopping app processes"
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" >/dev/null 2>&1; then
        kill "$pid" >/dev/null 2>&1 || true
      fi
    done
    for pid in "${pids[@]}"; do
      wait "$pid" >/dev/null 2>&1 || true
    done
  fi

  exit "$status"
}

start_service() {
  local name="$1"
  local dir="$2"
  shift 2

  log "Starting $name"
  (
    cd "$dir"
    exec "$@"
  ) > >(sed -u "s/^/[$name] /") 2> >(sed -u "s/^/[$name] /" >&2) &

  pids+=("$!")
  names+=("$name")
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

need_command uv
need_command npm

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  printf 'frontend/node_modules is missing. Run ./scripts/install.sh first.\n' >&2
  exit 1
fi

trap cleanup INT TERM EXIT

start_service "backend" "$ROOT_DIR/backend" \
  uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

start_service "frontend" "$ROOT_DIR/frontend" \
  npm run dev

log "App is starting"
printf 'Frontend: http://localhost:3000\n'
printf 'Backend:  http://localhost:8000\n'
printf 'Press Ctrl+C to stop.\n'

while true; do
  running_pids="$(jobs -r -p)"
  for i in "${!pids[@]}"; do
    pid="${pids[$i]}"
    if [[ $'\n'"$running_pids"$'\n' != *$'\n'"$pid"$'\n'* ]]; then
      status=0
      wait "$pid" || status=$?
      printf '\n%s exited with status %s\n' "${names[$i]}" "$status" >&2
      exit "$status"
    fi
  done
  sleep 1
done
