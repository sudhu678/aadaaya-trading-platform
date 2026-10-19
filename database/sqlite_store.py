"""Public SQLite storage infrastructure: read-only, parameterized, schema-aware.

Never opens private database paths implicitly or creates missing databases.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from fastapi import HTTPException

PUBLIC_TABLES = frozenset({'positions', 'portfolio_account_snapshots', 'public_position_snapshots'})


def public_db_path() -> Path:
    raw = os.getenv('TRADING_DB_PATH', '').strip()
    if not raw:
        raise HTTPException(503, 'Configure an existing public/demo TRADING_DB_PATH')
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise HTTPException(503, 'Configure an existing public/demo TRADING_DB_PATH')
    return path


def open_public_db() -> sqlite3.Connection:
    path = public_db_path()
    try:
        con = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA query_only=ON')
        return con
    except sqlite3.Error as exc:
        raise HTTPException(503, 'Unable to read public database') from exc


def has_public_table(con: sqlite3.Connection, table: str) -> bool:
    if table not in PUBLIC_TABLES:
        raise ValueError('Table is not in public schema allowlist')
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def validate_public_schema(con: sqlite3.Connection) -> dict[str, list[str]]:
    required = {
        'positions': {'position_id','portfolio_id','ticker','status','open_quantity','avg_entry_price','current_stop'},
    }
    result = {}
    for table in PUBLIC_TABLES:
        if not has_public_table(con, table):
            result[table] = ['missing table'] if table in required else []
            continue
        columns = {row['name'] for row in con.execute(f'PRAGMA table_info({table})')}
        result[table] = sorted(required.get(table, set()) - columns)
    return result
