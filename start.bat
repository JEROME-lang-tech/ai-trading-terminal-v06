@echo off
REM Start the AI Trading Engine dashboard (Windows)
cd /d "%~dp0"

python -c "import fastapi, uvicorn, sklearn" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install -r requirements.txt
)

echo.
echo   Dashboard: http://localhost:8000
echo   Press Ctrl+C to stop.
echo.
python -m uvicorn aitrader.dashboard.server:api --host 0.0.0.0 --port 8000
pause
