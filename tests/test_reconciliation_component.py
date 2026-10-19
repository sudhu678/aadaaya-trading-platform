import sqlite3
from fastapi.testclient import TestClient
from database.transaction_ledger import create_public_ledger, add_cash_event
from database.portfolio_reconciliation import compare_cash
from scripts.create_demo_db import create_demo_db
from dashboard.api.main import app


def setup(tmp_path, monkeypatch):
    demo = create_demo_db(str(tmp_path/'demo.sqlite3'))
    ledger = str(tmp_path/'cash.sqlite3')
    create_public_ledger(ledger)
    monkeypatch.setenv('TRADING_DB_PATH', str(demo))
    monkeypatch.setenv('PUBLIC_CASH_LEDGER_PATH', ledger)
    return ledger


def test_cash_matches_without_claiming_full_reconciliation(tmp_path, monkeypatch):
    ledger=setup(tmp_path,monkeypatch)
    add_cash_event(ledger,1,'fund','2026-01-01','DEPOSIT','10000')
    add_cash_event(ledger,1,'buy','2026-01-14','BUY','1000')
    result=TestClient(app).get('/api/portfolio/cash-reconciliation',params={'portfolio_id':1,'as_of':'2026-01-15'})
    assert result.status_code==200, result.text
    data=result.json()
    assert data['cash_matches'] is True
    assert data['full_portfolio_reconciled'] is False
    assert data['ledger_event_count']==2


def test_cash_mismatch_is_explicit(tmp_path,monkeypatch):
    ledger=setup(tmp_path,monkeypatch)
    add_cash_event(ledger,1,'fund','2026-01-01','DEPOSIT','10000')
    data=TestClient(app).get('/api/portfolio/cash-reconciliation',params={'portfolio_id':1,'as_of':'2026-01-15'}).json()
    assert data['cash_difference']==1000
    assert data['cash_matches'] is False


def test_missing_ledger_configuration_is_safe(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    monkeypatch.delenv('PUBLIC_CASH_LEDGER_PATH')
    response=TestClient(app).get('/api/portfolio/cash-reconciliation',params={'portfolio_id':1,'as_of':'2026-01-15'})
    assert response.status_code==503


def test_missing_snapshot_is_not_fabricated(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    response=TestClient(app).get('/api/portfolio/cash-reconciliation',params={'portfolio_id':1,'as_of':'2026-01-14'})
    assert response.status_code==404


def test_cutoff_excludes_future_cash_events(tmp_path,monkeypatch):
    ledger=setup(tmp_path,monkeypatch)
    add_cash_event(ledger,1,'a','2026-01-01','DEPOSIT','9000')
    add_cash_event(ledger,1,'b','2026-01-16','DEPOSIT','500')
    data=compare_cash(ledger,1,'2026-01-15','9000')
    assert data['cash_matches'] is True and data['ledger_event_count']==1


def test_missing_ledger_does_not_create_file(tmp_path):
    path=tmp_path/'absent.sqlite3'
    try: compare_cash(str(path),1,'2026-01-15','0')
    except FileNotFoundError: pass
    else: assert False
    assert not path.exists()
