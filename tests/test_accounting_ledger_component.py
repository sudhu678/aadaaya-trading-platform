import pytest
from database.cash_accounting import reconcile_cash


def test_cash_reconciliation():
    events = [
        {'event_id':'3','timestamp':'2026-01-03','kind':'SELL','amount':'250.00'},
        {'event_id':'1','timestamp':'2026-01-01','kind':'DEPOSIT','amount':'1000.00'},
        {'event_id':'2','timestamp':'2026-01-02','kind':'BUY','amount':'400.00'},
        {'event_id':'4','timestamp':'2026-01-04','kind':'FEE','amount':'2.50'},
    ]
    result = reconcile_cash('0.00',events)
    assert result['cash_balance'] == 847.5
    assert result['event_count'] == 4
    assert result['realized_pnl'] is None


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError):
        reconcile_cash(100,[{'event_id':'a','timestamp':'2026-01-01','kind':'BUY','amount':1},
                            {'event_id':'a','timestamp':'2026-01-02','kind':'SELL','amount':1}])

@pytest.mark.parametrize('amount',['NaN','Infinity','0.001',-1])
def test_invalid_amounts_rejected(amount):
    with pytest.raises(ValueError):
        reconcile_cash(100,[{'event_id':'a','timestamp':'2026-01-01','kind':'BUY','amount':amount}])


def test_overdraft_rejected():
    with pytest.raises(ValueError):
        reconcile_cash(10,[{'event_id':'a','timestamp':'2026-01-01','kind':'BUY','amount':11}])
