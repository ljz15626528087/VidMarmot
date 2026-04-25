@echo off
chcp 65001 >nul

cd /d "%~dp0"

:: 清除缓存
del /s /q __pycache__\*.pyc 2>nul
for /d %%d in (__pycache__) do rd /s /q "%%d" 2>nul

echo 正在激活 Videoer 环境并启动 GUI...

call C:\ProgramData\anaconda3\Scripts\activate.bat Videoer
if errorlevel 1 (
    echo [错误] 无法激活 Videoer 环境
    pause
    exit /b 1
)

cd /d "%~dp0"
python "%~dp0gui.py"
if errorlevel 1 (
    echo.
    echo [错误] 启动失败
    pause
)
