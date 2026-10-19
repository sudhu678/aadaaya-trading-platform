
import os
from fastapi.testclient import TestClient
from scripts.create_demo_db import create_demo_db
from dashboard.api.main import app

def test_matching_date_equity(tmp_path, monkeypatch):
    db = create_demo_db(str(tmp_path / 'demo.sqlite3'))
    monkeypatch.setenv('TRADING_DB_PATH', str(db))
    client = TestClient(app)
    response = client.post('/api/portfolio/valuation', json={
        'portfolio_id': 1, 'prices': {'DEMO': 110}, 'as_of': '2026-01-15'})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['equity'] == 10100.0
    assert data['cash_balance'] == 9000.0
    assert data['realized_pnl'] == 0.0

def test_mismatched_date_never_claims_equity(tmp_path, monkeypatch):
    db = create_demo_db(str(tmp_path / 'demo.sqlite3'))
    monkeypatch.setenv('TRADING_DB_PATH', str(db))
    data = TestClient(app).post('/api/portfolio/valuation', json={
        'portfolio_id': 1, 'prices': {'DEMO': 110}, 'as_of': '2026-01-16'}).json()
    assert data['equity'] is None

def test_missing_quote_never_claims_equity(tmp_path, monkeypatch):
    db = create_demo_db(str(tmp_path / 'demo.sqlite3'))
    monkeypatch.setenv('TRADING_DB_PATH', str(db))
    data = TestClient(app).post('/api/portfolio/valuation', json={
        'portfolio_id': 1, 'prices': {}, 'as_of': '2026-01-15'}).json()
    assert data['equity'] is None


def test_matching_older_snapshot_not_overridden_by_newer(tmp_path, monkeypatch):
    import sqlite3
    db = create_demo_db(str(tmp_path / 'demo.sqlite3'))
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO portfolio_account_snapshots VALUES (1,'2026-01-16',8000,100)")
    monkeypatch.setenv('TRADING_DB_PATH', str(db))
    data = TestClient(app).post('/api/portfolio/valuation', json={
        'portfolio_id': 1, 'prices': {'DEMO': 110}, 'as_of': '2026-01-15'}).json()
    assert data['equity'] == 10100.0
    assert data['accounting_as_of'] == '2026-01-15'
