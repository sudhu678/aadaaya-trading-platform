import sqlite3
import pytest
from database.transaction_ledger import create_public_ledger,add_cash_event,ledger_balance

def test_create_and_replay(tmp_path):
    path=str(tmp_path/'ledger.db');create_public_ledger(path)
    assert add_cash_event(path,1,'a','2026-01-01','DEPOSIT','100.00')['cash_balance']==100
    assert add_cash_event(path,1,'b','2026-01-02','BUY','35.25')['cash_balance']==64.75
    assert ledger_balance(path,1)['cash_balance']==64.75
    assert ledger_balance(path,1,as_of='2026-01-01')['cash_balance']==100

def test_duplicate_rejected_without_partial_write(tmp_path):
    path=str(tmp_path/'ledger.db');create_public_ledger(path)
    add_cash_event(path,1,'a','2026-01-01','DEPOSIT','10.00')
    with pytest.raises(ValueError): add_cash_event(path,1,'a','2026-01-02','DEPOSIT','10.00')
    assert ledger_balance(path,1)['event_count']==1

def test_negative_cash_rejected_atomically(tmp_path):
    path=str(tmp_path/'ledger.db');create_public_ledger(path)
    with pytest.raises(ValueError):add_cash_event(path,1,'a','2026-01-01','BUY','5.00')
    assert ledger_balance(path,1)['event_count']==0

def test_never_overwrite_existing_db(tmp_path):
    path=str(tmp_path/'ledger.db');create_public_ledger(path)
    with pytest.raises(FileExistsError):create_public_ledger(path)

def test_isolated_portfolios(tmp_path):
    path=str(tmp_path/'ledger.db');create_public_ledger(path)
    add_cash_event(path,1,'a','2026-01-01','DEPOSIT','10.00')
    add_cash_event(path,2,'a','2026-01-01','DEPOSIT','20.00')
    assert ledger_balance(path,2)['cash_balance']==20
    assert ledger_balance(path,1)['cash_balance']==10
