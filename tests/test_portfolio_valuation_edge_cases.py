from dashboard.api.valuation import value_positions


def test_missing_quote_never_understates_portfolio():
    rows = [{'ticker':'AAA','status':'OPEN','open_quantity':2,'avg_entry_price':10}, {'ticker':'BBB','status':'OPEN','open_quantity':3,'avg_entry_price':20}]
    result = value_positions(rows, {'AAA':12})
    assert result['valuation_complete'] is False
    assert result['market_value'] is None
    assert result['unrealized_pnl'] is None
    assert result['missing_prices'] == ['BBB']
    assert result['open_cost_basis'] == 80


def test_closed_positions_do_not_affect_open_valuation():
    rows = [{'ticker':'AAA','status':'CLOSED','open_quantity':10,'avg_entry_price':100}]
    result = value_positions(rows, {})
    assert result['valuation_complete'] is True
    assert result['open_cost_basis'] == 0
    assert result['market_value'] == 0
    assert result['equity'] is None


def test_nonfinite_position_is_rejected():
    import pytest
    rows = [{'ticker':'AAA','status':'OPEN','open_quantity':float('nan'),'avg_entry_price':10}]
    with pytest.raises(ValueError):
        value_positions(rows, {'AAA':12})
