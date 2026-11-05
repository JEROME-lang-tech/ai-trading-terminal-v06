#!/usr/bin/env bash
# Start the AI Trading Engine dashboard (Linux / macOS)
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

if ! "$PY" -c "import fastapi, uvicorn, sklearn" 2>/dev/null; then
  echo "Installing dependencies..."
  "$PY" -m pip install -r requirements.txt
fi

echo ""
echo "  Dashboard: http://localhost:8000"
echo "  Press Ctrl+C to stop."
echo ""
exec "$PY" -m uvicorn aitrader.dashboard.server:api --host 0.0.0.0 --port 8000
