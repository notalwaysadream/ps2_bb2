#!/usr/bin/env bash
set -e

echo "=== ASHA Voice Field Register Setup and Runner ==="

# Root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH."
    exit 1
fi

# 2. Setup Backend
echo "[1/3] Setting up backend environment..."
cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment in backend/.venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing backend dependencies..."
pip install -r requirements.txt --quiet

# Create default .env if it does not exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created backend/.env from .env.example (simulation mode active until API keys are added)."
fi

# 3. Setup Frontend
echo "[2/3] Setting up frontend..."
cd "$ROOT_DIR/frontend"

HAS_NPM=false
if command -v npm &> /dev/null; then
    HAS_NPM=true
    echo "Installing frontend npm packages..."
    npm install --silent
else
    echo "Notice: npm is not installed. You can still test backend and API endpoints."
fi

# 4. Start Both Applications
echo "[3/3] Starting applications..."
echo "--------------------------------------------------"
echo "Backend URL:  http://localhost:8000"
echo "API Docs:     http://localhost:8000/docs"
echo "WebSocket:    ws://localhost:8000/ws/audio"
if [ "$HAS_NPM" = true ]; then
    echo "Frontend URL: http://localhost:3000"
fi
echo "--------------------------------------------------"
echo "Press Ctrl+C to stop all services."

# Kill child jobs when exiting
cleanup() {
    echo ""
    echo "Stopping all running services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start backend
cd "$ROOT_DIR/backend"
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend if npm is present
if [ "$HAS_NPM" = true ]; then
    cd "$ROOT_DIR/frontend"
    npm run dev &
    FRONTEND_PID=$!
fi

# Wait for background jobs
wait
