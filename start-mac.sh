#!/bin/zsh
# ============================================================
#  SmartFarm — Mac Startup Script (No Docker)
#  Usage: ./start-mac.sh
#  Opens 2 terminal tabs: Backend | Frontend
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   SmartFarm — Starting Up (Mac / No Docker) ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Ensure PostgreSQL is running ────────────────────────
echo "▶  Checking PostgreSQL..."
if ! pg_isready -q 2>/dev/null; then
  echo "   Starting PostgreSQL via brew services..."
  brew services start postgresql@16 2>/dev/null || brew services start postgresql 2>/dev/null
  sleep 3
fi
echo "   ✅ PostgreSQL is running"

# ── 2. Ensure the database exists ──────────────────────────
echo "▶  Ensuring 'smartfarm' database exists..."
createdb smartfarm 2>/dev/null && echo "   ✅ Database created" || echo "   ✅ Database already exists"

# ── 3. Open Backend in a new Terminal tab ──────────────────
echo ""
echo "▶  Starting Backend (FastAPI) on http://localhost:8000 ..."
osascript <<EOF
tell application "Terminal"
  activate
  tell application "System Events" to keystroke "t" using command down
  delay 0.5
  do script "echo '── SmartFarm Backend ──' && cd \"${PROJECT_DIR}/backend\" && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" in front window
end tell
EOF

sleep 2

# ── 4. Open Frontend in a new Terminal tab ─────────────────
echo "▶  Starting Frontend (Vite) on http://localhost:5173 ..."
osascript <<EOF
tell application "Terminal"
  activate
  tell application "System Events" to keystroke "t" using command down
  delay 0.5
  do script "echo '── SmartFarm Frontend ──' && cd \"${PROJECT_DIR}/frontend\" && npm run dev -- --host" in front window
end tell
EOF

sleep 3

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          SmartFarm is Running! 🌱         ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Dashboard  →  http://localhost:5173     ║"
echo "║  API Docs   →  http://localhost:8000/api/docs ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  Your USB sensor is auto-detected automatically."
echo "  Just plug in your Arduino and readings will appear live."
echo ""
echo "  To stop: close the Backend and Frontend terminal tabs."
echo ""

# Open the dashboard in the default browser
open "http://localhost:5173"
