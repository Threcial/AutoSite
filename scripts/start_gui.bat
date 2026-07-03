@echo off
cd /d "%~dp0.."
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m autosite gui
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m autosite gui
) else (
    start "" pythonw -m autosite gui
)
