"""Public, opt-in FIFO position ledger. No strategy signals or execution automation."""
from __future__ import annotations
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from database.cash_accounting import money

DDL = """CREATE TABLE IF NOT EXISTS public_position_events (
 portfolio_id INTEGER NOT NULL CHECK(portfolio_id > 0),
 event_id TEXT NOT NULL, timestamp TEXT NOT NULL, ticker TEXT NOT NULL,
 side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
 quantity TEXT NOT NULL, unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents >= 0),
 fee_cents INTEGER NOT NULL CHECK(fee_cents >= 0),
 PRIMARY KEY(portfolio_id,event_id))"""

def quantity(value):
    try: d=Decimal(str(value))
    except Exception as exc: raise ValueError('Invalid quantity') from exc
    if not d.is_finite() or d <= 0 or d.as_tuple().exponent < -8:
        raise ValueError('Quantity must be positive with at most eight decimal places')
    return d

def timestamp(value):
    if not isinstance(value,str): raise ValueError('Invalid timestamp')
    try: dt=datetime.fromisoformat(value)
    except ValueError as exc: raise ValueError('Invalid ISO timestamp') from exc
    if dt.tzinfo is not None: raise ValueError('Use timezone-naive timestamps consistently')
    return dt.isoformat()

def replay(events):
    """FIFO long-only positions, with fees included in basis and realized P&L."""
    seen=set(); normalized=[]
    for e in events:
        eid=str(e.get('event_id','')).strip(); ticker=str(e.get('ticker','')).strip().upper()
        side=str(e.get('side','')).upper(); when=timestamp(e.get('timestamp'))
        if not eid or eid in seen or not ticker or not all(c.isalnum() or c in '.-' for c in ticker) or side not in ('BUY','SELL'):
            raise ValueError('Invalid or duplicate position event')
        seen.add(eid)
        normalized.append((when,eid,ticker,side,quantity(e.get('quantity')),money(e.get('unit_price')),money(e.get('fee','0'))))
    lots={}; realized=Decimal('0'); processed=0
    for _,_,ticker,side,qty,price,fee in sorted(normalized):
        book=lots.setdefault(ticker,[])
        if side=='BUY':
            book.append([qty,qty*price+fee])
        else:
            remaining=qty; basis=Decimal('0')
            while remaining>0:
                if not book: raise ValueError('Sell exceeds available position')
                lot_qty,lot_basis=book[0]
                take=min(remaining,lot_qty)
                used=lot_basis*take/lot_qty
                basis+=used
                if take==lot_qty: book.pop(0)
                else: book[0]=[lot_qty-take,lot_basis-used]
                remaining-=take
            realized+=qty*price-fee-basis
        processed+=1
    positions={}
    for ticker,book in sorted(lots.items()):
        qty=sum((q for q,_ in book),Decimal('0'))
        if qty:
            basis=sum((b for _,b in book),Decimal('0'))
            positions[ticker]={'quantity':str(qty.normalize()),'cost_basis':str(basis.quantize(Decimal('0.01'))),
                               'average_cost':str((basis/qty).quantize(Decimal('0.000001')))}
    return {'positions':positions,'realized_pnl':str(realized.quantize(Decimal('0.01'))),'event_count':processed,
            'note':'FIFO long-only, no corporate actions, shorts, FX, or wash-sale adjustments.'}

def create_position_ledger(path):
    target=Path(path)
    if target.exists(): raise FileExistsError('Refusing to overwrite database')
    target.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(target) as db: db.execute(DDL)

def _read(db,portfolio_id,as_of=None):
    sql='SELECT event_id,timestamp,ticker,side,quantity,unit_price_cents,fee_cents FROM public_position_events WHERE portfolio_id=?'
    args=[portfolio_id]
    if as_of is not None: sql+=' AND timestamp<=?';args.append(as_of)
    rows=db.execute(sql,args).fetchall()
    return [dict(event_id=r[0],timestamp=r[1],ticker=r[2],side=r[3],quantity=r[4],unit_price=Decimal(r[5])/100,fee=Decimal(r[6])/100) for r in rows]

def add_position_event(path,portfolio_id,event_id,when,ticker,side,qty,price,fee='0'):
    if isinstance(portfolio_id,bool) or not isinstance(portfolio_id,int) or portfolio_id<1: raise ValueError('Invalid portfolio')
    event=dict(event_id=event_id,timestamp=timestamp(when),ticker=ticker,side=side,quantity=str(quantity(qty)),unit_price=money(price),fee=money(fee))
    target=Path(path)
    if not target.is_file(): raise FileNotFoundError('Position ledger does not exist')
    with sqlite3.connect(target,timeout=5) as db:
        db.execute('BEGIN IMMEDIATE')
        result=replay(_read(db,portfolio_id)+[event])
        db.execute('INSERT INTO public_position_events VALUES (?,?,?,?,?,?,?,?)',
                   (portfolio_id,event_id,event['timestamp'],ticker.upper(),side.upper(),str(event['quantity']),int(event['unit_price']*100),int(event['fee']*100)))
    return result

def position_balance(path,portfolio_id,as_of):
    if not Path(path).is_file(): raise FileNotFoundError('Position ledger does not exist')
    with sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro',uri=True) as db:
        return replay(_read(db,portfolio_id,timestamp(as_of)))

def compare_positions(ledger_result,snapshot):
    """Compare replay to independently recorded as-of holdings; no silent zero fills."""
    expected={}
    for item in snapshot:
        ticker=str(item['ticker']).strip().upper()
        if ticker in expected: raise ValueError('Duplicate snapshot ticker')
        q=Decimal(str(item['quantity']))
        if not q.is_finite() or q<0: raise ValueError('Invalid snapshot quantity')
        if q: expected[ticker]=q
    actual={k:Decimal(v['quantity']) for k,v in ledger_result['positions'].items()}
    discrepancies=[{'ticker':t,'ledger_quantity':str(actual.get(t,Decimal('0'))),
                    'snapshot_quantity':str(expected.get(t,Decimal('0')))}
                   for t in sorted(actual.keys()|expected.keys()) if actual.get(t,Decimal('0'))!=expected.get(t,Decimal('0'))]
    return {'quantities_match':not discrepancies,'discrepancies':discrepancies,
            'ledger_realized_pnl':ledger_result['realized_pnl'], 'cost_basis_reconciled':False,
            'realized_pnl_reconciled':False,'full_portfolio_reconciled':False,
            'note':'Quantity-only reconciliation; FIFO cost basis is computed but not independently reconciled.'}
