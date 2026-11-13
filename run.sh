#!/usr/bin/env bash
set -e

# Clear screen for clean presentation
clear 2>/dev/null || true

echo "=================================================="
echo "    ASHA Voice Field Register Setup & Runner"
echo "=================================================="

# Root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH."
    exit 1
fi

# 2. Free up ports 8000 and 3000 if already in use from a previous run
echo "[1/4] Checking ports 8000 and 3000..."
for PORT in 8000 3000; do
    PID=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo "      Port $PORT is already in use by PID $PID. Freeing port..."
        kill -9 $PID 2>/dev/null || true
    fi
done

# 3. Setup Backend
echo "[2/4] Setting up backend virtual environment..."
cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
    echo "      Creating virtual environment in backend/.venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "      Checking backend dependencies..."
pip install -r requirements.txt --quiet

# Create default .env if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "      Created backend/.env from .env.example"
fi

# 4. Setup Frontend
echo "[3/4] Setting up frontend..."
cd "$ROOT_DIR/frontend"

HAS_NPM=false
if command -v npm &> /dev/null; then
    HAS_NPM=true
    if [ ! -d "node_modules" ]; then
        echo "      Installing frontend packages (npm install)..."
        npm install --silent
    else
        echo "      Frontend packages already installed."
    fi
else
    echo "      Notice: npm not found. You can still use the FastAPI UI at http://localhost:8000/ui"
fi

# 5. Helper function to open browser
open_browser() {
    local target_url="$1"
    sleep 2
    echo "      Opening $target_url in default browser..."
    if command -v open &> /dev/null; then
        open "$target_url"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$target_url" &> /dev/null
    elif command -v python3 &> /dev/null; then
        python3 -m webbrowser "$target_url" &> /dev/null
    fi
}

# 6. Start Applications
echo "[4/4] Starting applications..."
echo "=================================================="
if [ "$HAS_NPM" = true ]; then
    echo "  Main Dashboard:       http://localhost:3000"
fi
echo "  FastAPI Direct UI:    http://localhost:8000/ui"
echo "  API Documentation:    http://localhost:8000/docs"
echo "  WebSocket Endpoint:   ws://localhost:8000/ws/audio"
echo "=================================================="
echo "Press Ctrl+C at any time to cleanly stop all services."
echo ""

# Kill all background jobs cleanly on exit
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null || true
    # Ensure ports are free
    for PORT in 8000 3000; do
        PID=$(lsof -ti :$PORT 2>/dev/null || true)
        if [ -n "$PID" ]; then
            kill -9 $PID 2>/dev/null || true
        fi
    done
    echo "All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start backend
cd "$ROOT_DIR/backend"
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend if npm is available
if [ "$HAS_NPM" = true ]; then
    cd "$ROOT_DIR/frontend"
    npm run dev &
    FRONTEND_PID=$!
    # Automatically open browser to port 3000
    open_browser "http://localhost:3000" &
else
    # Automatically open browser to FastAPI UI at port 8000
    open_browser "http://localhost:8000/ui" &
fi

# Wait for background jobs
wait
