import pytest
from fastapi.testclient import TestClient
from dashboard.api.main import app
from scripts.create_demo_db import create_demo_db

@pytest.fixture
def client(tmp_path, monkeypatch):
    path=create_demo_db(str(tmp_path/'demo.sqlite3'))
    monkeypatch.setenv('TRADING_DB_PATH',str(path))
    return TestClient(app)

def test_health_and_read_only_positions(client):
    assert client.get('/api/health').json()['edition']=='public'
    response=client.get('/api/trades/positions',params={'portfolio_id':1})
    assert response.status_code==200
    assert len(response.json()['positions'])==2

def test_portfolio_valuation_contract(client):
    summary=client.get('/api/portfolio/summary',params={'portfolio_id':1})
    assert summary.status_code==200
    assert summary.json()['equity'] is None
    response=client.post('/api/portfolio/valuation',json={'portfolio_id':1,'prices':{'DEMO':110.0},'as_of':'2026-10-18'})
    assert response.status_code==200
    result=response.json()
    assert result['market_value']==1100.0
    assert result['unrealized_pnl']==100.0
    assert result['equity'] is None

def test_public_write_containment(client):
    assert client.post('/api/trades/open').status_code==410
    assert client.post('/api/trades/close').status_code==410
    assert client.post('/api/operations/scanner/runs',json={'tickers':'DEMO','db_write_mode':'LIVE'}).status_code==422
    assert client.post('/api/operations/manager/runs',json={'portfolio_id':1,'db_mode':'LIVE'}).status_code==422

def test_private_reports_unavailable(client):
    assert client.get('/api/backtests/example/sheets').status_code==410
