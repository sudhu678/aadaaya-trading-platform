"""Public, read-only position valuation using caller-supplied prices.

No trading execution, brokerage access, or proprietary strategy imports.
"""
from __future__ import annotations
from datetime import date
from math import isfinite
from typing import Mapping


def value_positions(rows: list[Mapping], prices: Mapping[str, float], *, as_of: str | None = None) -> dict:
    """Value open positions. Missing/invalid quotes never become zero-valued holdings."""
    holdings = []
    missing = []
    cost_basis = 0.0
    market_value = 0.0
    for row in rows:
        if str(row['status']).upper() != 'OPEN':
            continue
        ticker = str(row['ticker']).upper().strip()
        quantity = float(row['open_quantity'] or 0)
        entry = float(row['avg_entry_price'] or 0)
        if not (isfinite(quantity) and isfinite(entry) and quantity >= 0 and entry >= 0):
            raise ValueError('Invalid position quantities or cost basis')
        cost = quantity * entry
        cost_basis += cost
        price = prices.get(ticker)
        if price is None or not isinstance(price, (int, float)) or not isfinite(price) or price <= 0:
            missing.append(ticker)
            holdings.append({'ticker': ticker, 'quantity': quantity, 'cost_basis': round(cost, 2), 'last_price': None, 'market_value': None, 'unrealized_pnl': None})
            continue
        value = quantity * float(price)
        market_value += value
        holdings.append({'ticker': ticker, 'quantity': quantity, 'cost_basis': round(cost, 2), 'last_price': float(price), 'market_value': round(value, 2), 'unrealized_pnl': round(value - cost, 2)})
    complete = not missing
    return {'as_of': as_of, 'valuation_complete': complete, 'open_cost_basis': round(cost_basis, 2),
            'market_value': round(market_value, 2) if complete else None,
            'unrealized_pnl': round(market_value - cost_basis, 2) if complete else None,
            'missing_prices': sorted(set(missing)), 'holdings': holdings,
            'realized_pnl': None, 'equity': None,
            'data_note': 'Prices must be independently supplied and dated. Equity and realized P&L require cash and execution accounting.'}
