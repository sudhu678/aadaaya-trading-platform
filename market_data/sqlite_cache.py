"""Opt-in public SQLite OHLCV cache; separate from trading/portfolio databases."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

FIELDS = ('Open', 'High', 'Low', 'Close', 'Volume')

class DailyBarCache:
    def __init__(self, path: str):
        self.path = str(Path(path).expanduser().resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS daily_bars (
                ticker TEXT NOT NULL, date TEXT NOT NULL,
                open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
                close REAL NOT NULL, volume REAL NOT NULL,
                PRIMARY KEY (ticker, date))''')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def read(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        with self._connect() as con:
            rows = con.execute('SELECT date, open, high, low, close, volume FROM daily_bars '
                               'WHERE ticker=? AND date>=? AND date<=? ORDER BY date',
                               (ticker.upper(), start, end)).fetchall()
        if not rows:
            return pd.DataFrame(columns=FIELDS)
        frame = pd.DataFrame(rows, columns=('Date', *FIELDS))
        frame['Date'] = pd.to_datetime(frame['Date'])
        return frame.set_index('Date')

    def write(self, ticker: str, bars: pd.DataFrame) -> int:
        if bars.empty: return 0
        if not all(field in bars.columns for field in FIELDS):
            raise ValueError('Missing OHLCV fields')
        if not isinstance(bars.index, pd.DatetimeIndex):
            raise ValueError('Cache requires DatetimeIndex')
        records=[]
        for day, row in bars.iterrows():
            values = tuple(float(row[field]) for field in FIELDS)
            if not all(pd.notna(value) and abs(value) != float('inf') for value in values):
                raise ValueError('Non-finite OHLCV value')
            records.append((ticker.upper(), day.strftime('%Y-%m-%d'), *values))
        with self._connect() as con:
            con.executemany('INSERT OR REPLACE INTO daily_bars VALUES (?,?,?,?,?,?,?)', records)
        return len(records)
