@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo   ASHA Voice Field Register Setup and Runner
echo ==================================================

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: python is not found in PATH.
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

:: 2. Setup Backend
echo.
echo [1/3] Setting up backend environment...
cd /d "%ROOT_DIR%backend"

if not exist .venv (
    echo Creating virtual environment in backend\.venv...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo Installing backend dependencies...
pip install -r requirements.txt --quiet

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo Created backend\.env from .env.example
    )
)

:: 3. Setup Frontend
echo.
echo [2/3] Setting up frontend...
cd /d "%ROOT_DIR%frontend"

set HAS_NPM=0
where npm >nul 2>nul
if %errorlevel% equ 0 (
    set HAS_NPM=1
    echo Installing frontend packages...
    call npm install --silent
) else (
    echo Notice: npm is not found in PATH. You can still test the backend.
)

:: 4. Start Applications
echo.
echo [3/3] Starting applications...
echo --------------------------------------------------
echo Backend URL:  http://localhost:8000
echo API Docs:     http://localhost:8000/docs
echo WebSocket:    ws://localhost:8000/ws/audio
if !HAS_NPM! equ 1 (
    echo Frontend URL: http://localhost:3000
)
echo --------------------------------------------------
echo Close the terminal windows to stop the services.
echo.

:: Launch Backend in a new window
start "ASHA Backend (FastAPI)" cmd /k "cd /d "%ROOT_DIR%backend" && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Launch Frontend in a new window if npm is present
if !HAS_NPM! equ 1 (
    start "ASHA Frontend (Vite)" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"
)

echo Both services are now running in separate windows.
pause
