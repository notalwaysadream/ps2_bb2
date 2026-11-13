@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo     ASHA Voice Field Register Setup ^& Runner
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

:: 2. Setup Backend Environment
echo.
echo [1/3] Setting up backend virtual environment...
cd /d "%ROOT_DIR%backend"

if not exist .venv (
    echo       Creating virtual environment in backend\.venv...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo       Checking backend dependencies...
pip install -r requirements.txt --quiet

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo       Created backend\.env from .env.example
    )
)

:: 3. Setup Frontend Environment
echo.
echo [2/3] Setting up frontend...
cd /d "%ROOT_DIR%frontend"

set HAS_NPM=0
where npm >nul 2>nul
if %errorlevel% equ 0 (
    set HAS_NPM=1
    if not exist node_modules (
        echo       Installing frontend packages (npm install)...
        call npm install --silent
    ) else (
        echo       Frontend packages already installed.
    )
) else (
    echo       Notice: npm not found. You can still use the FastAPI UI at http://localhost:8000/ui
)

:: 4. Start Applications
echo.
echo [3/3] Starting applications...
echo ==================================================
if !HAS_NPM! equ 1 (
    echo   Main Dashboard:       http://localhost:3000
)
echo   FastAPI Direct UI:    http://localhost:8000/ui
echo   API Documentation:    http://localhost:8000/docs
echo   WebSocket Endpoint:   ws://localhost:8000/ws/audio
echo ==================================================
echo Close the opened terminal windows to stop the services.
echo.

:: Launch Backend in a separate window
start "ASHA Backend (FastAPI)" cmd /k "cd /d "%ROOT_DIR%backend" && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Launch Frontend in a separate window if npm is present
if !HAS_NPM! equ 1 (
    start "ASHA Frontend (Vite)" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"
)

:: Wait 3 seconds for servers to initialize, then launch default browser
echo Opening frontend in your default browser...
timeout /t 3 /nobreak >nul

if !HAS_NPM! equ 1 (
    start "" "http://localhost:3000"
) else (
    start "" "http://localhost:8000/ui"
)

echo Applications are running.
pause
