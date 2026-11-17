#!/usr/bin/env bash
set -euo pipefail
case "${1:-serve-all}" in
  serve|serve-all)
    if command -v cron >/dev/null 2>&1; then
      cron
    fi
    mkdir -p "${GEMINI_WORKDIR:-/workspace}"
    if [ ! -e "${GEMINI_WORKDIR:-/workspace}/GEMINI.md" ]; then
      cp /app/GEMINI.md "${GEMINI_WORKDIR:-/workspace}/GEMINI.md"
    fi
    ;;
esac
if [ $# -eq 0 ]; then set -- serve-all; fi
exec python /app/launcher.py "$@"
