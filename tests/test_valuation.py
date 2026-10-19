import sqlite3
from fastapi.testclient import TestClient
from dashboard.api.main import app
from dashboard.api.valuation import value_positions

def test_complete_valuation():
    r=value_positions([{'ticker':'AAA','status':'OPEN','open_quantity':2,'avg_entry_price':10}], {'AAA':12}, as_of='2026-10-18')
    assert (r['market_value'],r['unrealized_pnl'],r['equity']) == (24,4,None)
    assert r['valuation_complete']

def test_missing_price_not_zero():
    r=value_positions([{'ticker':'AAA','status':'OPEN','open_quantity':2,'avg_entry_price':10}], {})
    assert r['market_value'] is None and r['missing_prices']==['AAA']

def test_closed_positions_excluded():
    r=value_positions([{'ticker':'AAA','status':'CLOSED','open_quantity':0,'avg_entry_price':10}], {})
    assert r['market_value']==0 and r['open_cost_basis']==0

def test_api_valuation(tmp_path,monkeypatch):
    p=tmp_path/'demo.db'
    c=sqlite3.connect(p)
    c.execute('CREATE TABLE positions (position_id INTEGER, portfolio_id INTEGER, ticker TEXT, status TEXT, open_quantity REAL, avg_entry_price REAL, current_stop REAL)')
    c.execute("INSERT INTO positions VALUES (1,1,'AAA','OPEN',3,20,15)")
    c.commit();c.close()
    monkeypatch.setenv('TRADING_DB_PATH',str(p))
    response=TestClient(app).post('/api/portfolio/valuation',json={'portfolio_id':1,'prices':{'AAA':25},'as_of':'2026-10-18'})
    assert response.status_code==200
    assert response.json()['unrealized_pnl']==15
    assert response.json()['equity'] is None
