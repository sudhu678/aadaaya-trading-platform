#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
[ -f demo_positions.sqlite3 ] || .venv/bin/python -m scripts.create_demo_db --out demo_positions.sqlite3
export TRADING_DB_PATH="$PWD/demo_positions.sqlite3"
.venv/bin/python run_dashboard_api.py
