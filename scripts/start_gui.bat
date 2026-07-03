@echo off
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m autosite gui
) else (
    python -m autosite gui
)
if errorlevel 1 (
    echo.
    echo GUI 启动失败，按任意键退出...
    pause >nul
)
