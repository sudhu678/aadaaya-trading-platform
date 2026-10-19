"""Public read-only trade routes. Never imports production trading or execution modules."""
from __future__ import annotations
import os, sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
router = APIRouter(prefix='/api/trades', tags=['Public trades'])

from database.sqlite_store import open_public_db

def _db():
    return open_public_db()

@router.get('/positions')
def positions(portfolio_id:int=Query(ge=1), limit:int=Query(100,ge=1,le=500)):
    con=_db()
    try:
        rows=con.execute('SELECT position_id, portfolio_id, ticker, status, open_quantity, avg_entry_price, current_stop FROM positions WHERE portfolio_id=? ORDER BY position_id DESC LIMIT ?', (portfolio_id,limit)).fetchall()
        return {'positions':[dict(r) for r in rows]}
    except sqlite3.Error as exc:
        raise HTTPException(503,'Public position query unavailable for this database schema') from exc
    finally: con.close()

@router.post('/open',status_code=410)
def open_trade():
    raise HTTPException(410,'Trade writes are disabled in the public edition')

@router.post('/close',status_code=410)
def close_trade():
    raise HTTPException(410,'Trade writes are disabled in the public edition')
