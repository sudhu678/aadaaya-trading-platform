@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" ( py -m venv .venv || exit /b 1 )
".venv\Scripts\python.exe" -m pip install -r requirements.txt || exit /b 1
if not exist "demo_positions.sqlite3" ( ".venv\Scripts\python.exe" -m scripts.create_demo_db --out demo_positions.sqlite3 || exit /b 1 )
set "TRADING_DB_PATH=%CD%\demo_positions.sqlite3"
".venv\Scripts\python.exe" run_dashboard_api.py
