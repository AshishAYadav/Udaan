#!/usr/bin/env bash
# Start the React dev server on :5173, installing dependencies on first run.
set -euo pipefail
cd "$(dirname "$0")/frontend"
[ -d node_modules ] || npm install
exec npm run dev
