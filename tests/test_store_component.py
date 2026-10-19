import sqlite3
import pytest
from fastapi import HTTPException
from database.sqlite_store import open_public_db, has_public_table, validate_public_schema
from scripts.create_demo_db import create_demo_db

def test_readonly_schema_and_writes_blocked(tmp_path, monkeypatch):
    path = create_demo_db(str(tmp_path/'demo.sqlite3'))
    monkeypatch.setenv('TRADING_DB_PATH', str(path))
    con = open_public_db()
    try:
        assert has_public_table(con, 'positions')
        assert validate_public_schema(con)['positions'] == []
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM positions")
    finally:
        con.close()

def test_missing_db_is_not_created(tmp_path, monkeypatch):
    path=tmp_path/'missing.sqlite3'
    monkeypatch.setenv('TRADING_DB_PATH', str(path))
    with pytest.raises(HTTPException) as exc:
        open_public_db()
    assert exc.value.status_code == 503
    assert not path.exists()

def test_unknown_table_is_not_exposed(tmp_path, monkeypatch):
    path=create_demo_db(str(tmp_path/'demo.sqlite3'))
    monkeypatch.setenv('TRADING_DB_PATH', str(path))
    con=open_public_db()
    try:
        with pytest.raises(ValueError):
            has_public_table(con, 'private_table')
    finally: con.close()
