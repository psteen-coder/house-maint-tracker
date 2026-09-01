@echo off
cd /d "%~dp0"
echo House Maint Tracker — installing if needed, then starting on port 8000
if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  python -m venv .venv
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Open http://127.0.0.1:8000
echo Login: patrick@1944dinius.local / adminpass
echo Leave this window open. Ctrl+C stops the server.
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
