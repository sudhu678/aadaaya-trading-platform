"""Read-only cash comparison. No inference of trades, positions or realized returns."""
from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from database.cash_accounting import money
from database.transaction_ledger import ledger_balance


def compare_cash(ledger_path: str, portfolio_id: int, as_of: str,
                 snapshot_cash: object, opening_cash: object = '0.00') -> dict:
    """Compare two independently supplied cash records at the same cutoff.

    This does NOT establish that holdings, fills, cost basis or P&L reconcile.
    The ledger must be explicitly provided; no private database discovery.
    """
    if not isinstance(portfolio_id, int) or isinstance(portfolio_id, bool) or portfolio_id < 1:
        raise ValueError('Invalid portfolio ID')
    if not as_of or len(as_of) != 10:
        raise ValueError('An explicit YYYY-MM-DD cutoff is required')
    if not Path(ledger_path).is_file():
        raise FileNotFoundError('Public cash ledger not found')
    snapshot = money(snapshot_cash)
    balance = ledger_balance(ledger_path, portfolio_id, opening_cash, as_of=as_of+'T23:59:59.999999')
    ledger = money(balance['cash_balance'])
    delta = ledger - snapshot
    return {'portfolio_id': portfolio_id, 'as_of': as_of,
            'ledger_cash': float(ledger), 'snapshot_cash': float(snapshot),
            'cash_difference': float(delta), 'cash_matches': delta == Decimal('0.00'),
            'ledger_event_count': balance['event_count'],
            'holdings_reconciled': False, 'realized_pnl_reconciled': False,
            'full_portfolio_reconciled': False,
            'note': 'Cash-only comparison. Position quantities, trade fills, cost basis and realized P&L are not validated.'}
