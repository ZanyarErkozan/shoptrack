@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
)
if not exist shoptrack.db (
  .venv\Scripts\python -m scripts.seed
)
echo.
echo ShopTrack is starting...
echo   PC:    http://127.0.0.1:7070
echo   Phone: http://YOUR-PC-IP:7070  (same Wi-Fi)
echo.
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 7070
pause
