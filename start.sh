#!/bin/bash
# ────────────────────────────────────────────
# Karandeni Investment – Startup Script
# Starts MongoDB and the Flask API server
# Usage: ./start.sh
# ────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

# Determine which Python binary to use
if [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

echo "════════════════════════════════════════"
echo "  Karandeni Investment – Startup"
echo "════════════════════════════════════════"

# ── 1. Start MongoDB ───────────────────────
echo ""
if pgrep -x "mongod" >/dev/null; then
  echo "▶ MongoDB is already running."
else
  echo "▶ Starting MongoDB..."
  brew services start mongodb-community 2>/dev/null || echo "  (MongoDB may already be running)"
  # Wait for MongoDB to be ready
  sleep 2
fi

# ── 2. Seed the database (safe to run multiple times) ──
echo ""
echo "▶ Seeding database..."
cd "$BACKEND_DIR"
"$PYTHON_BIN" seed.py

# ── 3. Start Flask API ─────────────────────
echo ""
echo "▶ Starting Flask API on http://localhost:5001"
echo "  Press Ctrl+C to stop."
echo ""
"$PYTHON_BIN" app.py
