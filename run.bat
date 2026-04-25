@echo off
chcp 65001 >nul

cd /d "%~dp0"

:: clean cache
del /s /q __pycache__\*.pyc 2>nul
for /d %%d in (__pycache__) do rd /s /q "%%d" 2>nul

echo Starting VidMarmot...

python "%~dp0gui.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Startup failed. Make sure Python and dependencies are installed.
    pause
)
