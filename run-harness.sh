#!/usr/bin/env bash
# Native launcher. Load .env as exported variables before starting any process.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
if [ -f "${HARNESS_ENV_FILE:-.env}" ]; then
  set -a
  source "${HARNESS_ENV_FILE:-.env}"
  set +a
fi
PYTHON_BIN="${HARNESS_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: create .venv and install api/requirements.txt (see README)." >&2
  exit 1
fi
export GEMINI_WORKDIR="${GEMINI_WORKDIR:-$PROJECT_DIR/workspace}"
export SLACK_UPLOAD_DIR="${SLACK_UPLOAD_DIR:-$GEMINI_WORKDIR/slack_uploads}"
export GEMINI_SCHEDULES_FILE="${GEMINI_SCHEDULES_FILE:-$GEMINI_WORKDIR/schedules.json}"
export GEMINI_CRON_LOG="${GEMINI_CRON_LOG:-$GEMINI_WORKDIR/cron.log}"
export HARNESS_HOST="${HARNESS_HOST:-127.0.0.1}"
export HARNESS_PORT="${HARNESS_PORT:-8081}"
export GEMINI_REMOTE_URL="${GEMINI_REMOTE_URL:-${HARNESS_URL:-http://127.0.0.1:$HARNESS_PORT}}"
mkdir -p "$GEMINI_WORKDIR"
if [ $# -eq 0 ]; then set -- serve-all; fi
exec "$PYTHON_BIN" "$PROJECT_DIR/api/launcher.py" "$@"
