#!/usr/bin/env bash
# Start the FastAPI backend on :8000, creating the virtualenv on first run.
set -euo pipefail
cd "$(dirname "$0")/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/uvicorn app.main:app --reload --host "${BACKEND_HOST:-0.0.0.0}" --port "${BACKEND_PORT:-8000}"
