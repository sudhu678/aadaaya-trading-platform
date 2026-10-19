import sqlite3
import pytest
from fastapi.testclient import TestClient
from database.position_accounting import create_position_ledger,add_position_event,position_balance,compare_positions,replay
from scripts.create_demo_db import create_demo_db
from dashboard.api.main import app

def test_fifo_and_fees():
    events=[dict(event_id='a',timestamp='2026-01-01',ticker='ABC',side='BUY',quantity=2,unit_price='10',fee='1'),
            dict(event_id='b',timestamp='2026-01-02',ticker='ABC',side='BUY',quantity=1,unit_price='20',fee='0'),
            dict(event_id='c',timestamp='2026-01-03',ticker='ABC',side='SELL',quantity=1,unit_price='30',fee='1')]
    out=replay(events)
    assert out['realized_pnl']=='18.50'
    assert out['positions']['ABC']['quantity']=='2'
    assert out['positions']['ABC']['cost_basis']=='30.50'

def test_oversell_rejected():
    with pytest.raises(ValueError,match='Sell exceeds'): replay([dict(event_id='x',timestamp='2026-01-01',ticker='ABC',side='SELL',quantity=1,unit_price=10)])

def test_atomic_and_date_cutoff(tmp_path):
    path=str(tmp_path/'pos.sqlite3');create_position_ledger(path)
    add_position_event(path,1,'a','2026-01-01','ABC','BUY','2','10')
    with pytest.raises(ValueError):add_position_event(path,1,'b','2026-01-02','ABC','SELL','3','10')
    add_position_event(path,1,'c','2026-01-03','ABC','SELL','1','20')
    assert position_balance(path,1,'2026-01-02T23:59:59')['positions']['ABC']['quantity']=='2'
    assert position_balance(path,1,'2026-01-04')['positions']['ABC']['quantity']=='1'
    with sqlite3.connect(path) as db: assert db.execute('SELECT count(*) FROM public_position_events').fetchone()[0]==2

def test_discrepancy_and_no_full_reconciliation():
    ledger=replay([dict(event_id='a',timestamp='2026-01-01',ticker='ABC',side='BUY',quantity=2,unit_price=10)])
    result=compare_positions(ledger,[{'ticker':'ABC','quantity':1}])
    assert result['discrepancies'] and not result['full_portfolio_reconciled']

def test_api_dated_snapshot(tmp_path,monkeypatch):
    db=create_demo_db(str(tmp_path/'demo.sqlite3'))
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE public_position_snapshots(portfolio_id INTEGER,as_of TEXT,ticker TEXT,quantity TEXT)')
        con.execute('INSERT INTO public_position_snapshots VALUES (1,?,?,?)',('2026-01-15','DEMO','10'))
    path=str(tmp_path/'pos.sqlite3');create_position_ledger(path)
    add_position_event(path,1,'a','2026-01-01','DEMO','BUY','10','100')
    monkeypatch.setenv('TRADING_DB_PATH',str(db));monkeypatch.setenv('PUBLIC_POSITION_LEDGER_PATH',path)
    response=TestClient(app).get('/api/portfolio/position-reconciliation',params={'portfolio_id':1,'as_of':'2026-01-15'})
    assert response.status_code==200,response.text
    assert response.json()['quantities_match'] is True
    assert response.json()['full_portfolio_reconciled'] is False

def test_missing_snapshot_not_fabricated(tmp_path,monkeypatch):
    db=create_demo_db(str(tmp_path/'demo.sqlite3'))
    monkeypatch.setenv('TRADING_DB_PATH',str(db));monkeypatch.setenv('PUBLIC_POSITION_LEDGER_PATH',str(tmp_path/'missing.sqlite3'))
    assert TestClient(app).get('/api/portfolio/position-reconciliation',params={'portfolio_id':1,'as_of':'2026-01-15'}).status_code==404
