"""Generate synthetic demo positions; never use private trading data."""
from pathlib import Path
import sqlite3, argparse

def create_demo_db(path: str):
    target=Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as con:
        con.execute("""CREATE TABLE positions (position_id INTEGER PRIMARY KEY, portfolio_id INTEGER NOT NULL, ticker TEXT NOT NULL, status TEXT NOT NULL, open_quantity INTEGER NOT NULL, avg_entry_price REAL NOT NULL, current_stop REAL)""")
        con.executemany("INSERT INTO positions VALUES (?,?,?,?,?,?,?)",[(1,1,'DEMO', 'OPEN',10,100.0,95.0),(2,1,'EXAMPLE','CLOSED',0,50.0,None)])
        con.execute("""CREATE TABLE portfolio_account_snapshots (
            portfolio_id INTEGER NOT NULL, as_of TEXT NOT NULL,
            cash_balance REAL NOT NULL, realized_pnl REAL NOT NULL,
            PRIMARY KEY(portfolio_id, as_of))""")
        con.execute("INSERT INTO portfolio_account_snapshots VALUES (1,'2026-01-15',9000.0,0.0)")
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='demo_positions.sqlite3')
    print(create_demo_db(parser.parse_args().out))
