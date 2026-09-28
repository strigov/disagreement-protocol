#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SKIP_BACKEND=0
SKIP_FRONTEND=0

usage() {
  cat <<'USAGE'
Usage: ./scripts/install.sh [options]

Install local development dependencies.

Options:
  --skip-backend    Do not install backend dependencies.
  --skip-frontend   Do not install frontend dependencies.
  -h, --help        Show this help.
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-backend)
      SKIP_BACKEND=1
      ;;
    --skip-frontend)
      SKIP_FRONTEND=1
      ;;
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

if [[ "$SKIP_BACKEND" -eq 0 ]]; then
  need_command uv
  log "Installing backend dependencies with Python 3.12"
  (
    cd "$ROOT_DIR/backend"
    uv sync --frozen --python 3.12 --extra dev
    uv run python - <<'PY'
import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit(f"Expected Python 3.12.x, got {sys.version.split()[0]}")
PY
  )
fi

if [[ "$SKIP_FRONTEND" -eq 0 ]]; then
  need_command npm
  log "Installing frontend dependencies"
  (cd "$ROOT_DIR/frontend" && npm ci)
fi

log "Install complete"
printf 'Start the app with: ./scripts/start.sh\n'
