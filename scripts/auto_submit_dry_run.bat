@echo off
cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    set PY=.venv\Scripts\python.exe
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Please install Python 3.
        echo.
        echo 未检测到 .venv，请先安装依赖：
        echo   python -m venv .venv
        echo   .venv\Scripts\pip install -r requirements.txt
        pause
        exit /b 1
    )
    set PY=python
)

echo [INFO] Running auto-submit in dry-run mode...
echo.
%PY% src/main.py auto-submit --dry-run
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [INFO] Dry-run completed. No changes were made.
echo.
pause
exit /b %EXIT_CODE%
