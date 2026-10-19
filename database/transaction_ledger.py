"""Opt-in public transaction ledger; no private database migration or trading logic."""
from __future__ import annotations
import sqlite3
from decimal import Decimal
from database.cash_accounting import reconcile_cash, money

SCHEMA = """CREATE TABLE IF NOT EXISTS public_cash_events (
 portfolio_id INTEGER NOT NULL CHECK(portfolio_id > 0),
 event_id TEXT NOT NULL,
 timestamp TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('DEPOSIT','WITHDRAWAL','BUY','SELL','FEE','DIVIDEND')),
 amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
 PRIMARY KEY (portfolio_id, event_id)
)"""

def create_public_ledger(path: str) -> None:
    """Create a new standalone public ledger; never touch the private portfolio DB."""
    from pathlib import Path
    target=Path(path)
    if target.exists():
        raise FileExistsError('Refusing to overwrite an existing database')
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as con:
        con.execute(SCHEMA)

def add_cash_event(path: str, portfolio_id: int, event_id: str, timestamp: str,
                   kind: str, amount: object, opening_cash: object = '0.00') -> dict:
    """Atomically validate replay before inserting an event. A standalone opt-in write API."""
    if portfolio_id < 1 or not event_id.strip() or not timestamp.strip():
        raise ValueError('Invalid portfolio, event ID, or timestamp')
    if kind not in {'DEPOSIT','WITHDRAWAL','BUY','SELL','FEE','DIVIDEND'}:
        raise ValueError('Unsupported event kind')
    cents=money(amount)*100
    if cents < 0: raise ValueError('Negative event amount')
    with sqlite3.connect(path, timeout=5) as con:
        con.execute('BEGIN IMMEDIATE')
        # No implicit schema creation or modification.
        rows=con.execute('SELECT event_id,timestamp,kind,amount_cents FROM public_cash_events WHERE portfolio_id=?',(portfolio_id,)).fetchall()
        events=[{'event_id':r[0],'timestamp':r[1],'kind':r[2], 'amount':str(Decimal(r[3])/100)} for r in rows]
        events.append({'event_id':event_id,'timestamp':timestamp,'kind':kind,'amount':str(Decimal(cents)/100)})
        result=reconcile_cash(opening_cash,events)
        con.execute('INSERT INTO public_cash_events VALUES (?,?,?,?,?)', (portfolio_id,event_id,timestamp,kind,int(cents)))
    return result

def ledger_balance(path: str, portfolio_id: int, opening_cash: object='0.00', as_of: str | None=None) -> dict:
    """Read only; report event count and replayed cash, never infer P&L."""
    with sqlite3.connect(f'file:{__import__("pathlib").Path(path).resolve().as_posix()}?mode=ro',uri=True) as con:
        sql='SELECT event_id,timestamp,kind,amount_cents FROM public_cash_events WHERE portfolio_id=?'
        params=[portfolio_id]
        if as_of is not None:
            sql+=' AND timestamp<=?'; params.append(as_of)
        rows=con.execute(sql,params).fetchall()
    return reconcile_cash(opening_cash, [{'event_id':r[0],'timestamp':r[1],'kind':r[2], 'amount':str(Decimal(r[3])/100)} for r in rows])
