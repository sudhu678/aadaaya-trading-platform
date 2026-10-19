"""Read-only public portfolio API; price inputs are explicit, never fabricated."""
from __future__ import annotations
import sqlite3
import os
from datetime import date
from database.portfolio_reconciliation import compare_cash
from database.position_accounting import position_balance, compare_positions
from math import isfinite
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from database.sqlite_store import open_public_db as _db, has_public_table
from .valuation import value_positions

router = APIRouter(prefix='/api/portfolio', tags=['Public portfolio'])

class ValuationRequest(BaseModel):
    portfolio_id: int = Field(ge=1)
    prices: dict[str, float] = Field(default_factory=dict)
    as_of: str | None = None

def _account_snapshot(portfolio_id: int, as_of: str | None):
    # Optional public accounting snapshot. No inference from open positions.
    con = _db()
    try:
        if not has_public_table(con, 'portfolio_account_snapshots'):
            return None
        rows = con.execute(
            "SELECT cash_balance, realized_pnl, as_of FROM portfolio_account_snapshots "
            "WHERE portfolio_id=? AND as_of=? LIMIT 1", (portfolio_id, as_of)
        ).fetchall()
        if not rows:
            return None
        row = rows[0]
        cash, realized = float(row['cash_balance']), float(row['realized_pnl'])
        if not all(map(isfinite, (cash, realized))):
            raise HTTPException(422, 'Invalid accounting snapshot')
        return {'cash_balance': round(cash, 2), 'realized_pnl': round(realized, 2),
                'accounting_as_of': row['as_of']}
    except sqlite3.Error as exc:
        raise HTTPException(503, 'Public accounting snapshot schema unavailable') from exc
    finally:
        con.close()

def _positions(portfolio_id: int):
    con = _db()
    try:
        return [dict(r) for r in con.execute('SELECT ticker, status, open_quantity, avg_entry_price FROM positions WHERE portfolio_id=?', (portfolio_id,)).fetchall()]
    except sqlite3.Error as exc:
        raise HTTPException(503, 'Public portfolio schema unavailable') from exc
    finally:
        con.close()

@router.get('/summary')
def summary(portfolio_id: int = Query(ge=1)):
    rows = _positions(portfolio_id)
    open_rows = [r for r in rows if str(r['status']).upper() == 'OPEN']
    try:
        result = value_positions(rows, {})
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, 'Invalid position data') from exc
    return {'portfolio_id': portfolio_id, 'total_positions': len(rows), 'position_accounting': len(open_rows),
            'closed_positions': len(rows)-len(open_rows), **result}

@router.post('/valuation')
def valuation(request: ValuationRequest):
    rows = _positions(request.portfolio_id)
    try:
        result = value_positions(rows, {k.upper().strip(): v for k,v in request.prices.items()}, as_of=request.as_of)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, 'Invalid valuation input or position data') from exc
    snapshot = _account_snapshot(request.portfolio_id, request.as_of)
    if snapshot:
        result['cash_balance'] = snapshot['cash_balance']
        result['realized_pnl'] = snapshot['realized_pnl']
        result['accounting_as_of'] = snapshot['accounting_as_of']
        # Equity is meaningful only with all open positions priced and a cash snapshot
        # for the same as-of date. No implicit synchronization.
        if (result['valuation_complete'] and request.as_of is not None
                and request.as_of == snapshot['accounting_as_of']):
            result['equity'] = round(snapshot['cash_balance'] + result['market_value'], 2)
        result['data_note'] = (
            'Cash and realized P&L are supplied by an optional external accounting '
            'snapshot; equity requires complete prices and matching as-of dates. '
            'No ledger reconciliation or liability accounting is implied.'
        )
    return {'portfolio_id': request.portfolio_id, **result}


@router.get('/cash-reconciliation')
def cash_reconciliation(portfolio_id: int = Query(ge=1), as_of: date = Query(...)):
    """Opt-in read-only comparison of an explicitly configured public ledger and snapshot."""
    ledger_path = os.getenv('PUBLIC_CASH_LEDGER_PATH', '').strip()
    if not ledger_path:
        raise HTTPException(503, 'Configure PUBLIC_CASH_LEDGER_PATH to enable cash comparison')
    cutoff = as_of.isoformat()
    snapshot = _account_snapshot(portfolio_id, cutoff)
    if snapshot is None:
        raise HTTPException(404, 'No matching public accounting snapshot for requested date')
    try:
        return compare_cash(ledger_path, portfolio_id, cutoff, snapshot['cash_balance'])
    except (FileNotFoundError, sqlite3.Error) as exc:
        raise HTTPException(503, 'Public cash ledger unavailable') from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/position-reconciliation')
def position_reconciliation(portfolio_id: int = Query(ge=1), as_of: date = Query(...)):
    """Compare opt-in FIFO ledger against independently stored dated position snapshots."""
    path=os.getenv('PUBLIC_POSITION_LEDGER_PATH','').strip()
    if not path:
        raise HTTPException(503,'Configure PUBLIC_POSITION_LEDGER_PATH')
    con=_db()
    try:
        if not has_public_table(con,'public_position_snapshots'):
            raise HTTPException(404,'No dated public position snapshot table')
        rows=con.execute('SELECT ticker, quantity FROM public_position_snapshots WHERE portfolio_id=? AND as_of=?',
                         (portfolio_id,as_of.isoformat())).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(503,'Public position snapshot schema unavailable') from exc
    finally: con.close()
    if not rows: raise HTTPException(404,'No position snapshots for this date')
    try:
        result=compare_positions(position_balance(path,portfolio_id,as_of.isoformat()+'T23:59:59.999999'),[dict(r) for r in rows])
        return {'portfolio_id':portfolio_id,'as_of':as_of.isoformat(),**result}
    except (FileNotFoundError,sqlite3.Error) as exc:
        raise HTTPException(503,'Public position ledger unavailable') from exc
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
