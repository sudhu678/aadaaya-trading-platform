"""Independent educational daily-bar backtest engine.

Signals are computed from completed bars and filled at the next session open.
No private strategy, manager, or execution imports are used.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import pandas as pd
import numpy as np


@dataclass
class PublicBacktest:
    initial_cash: float = 10000.0
    stop_pct: float = 0.05
    risk_fraction: float = 0.01
    fast: int = 20
    slow: int = 50

    def __post_init__(self):
        if self.initial_cash <= 0 or not (0 < self.stop_pct < 1) or not (0 < self.risk_fraction <= 1):
            raise ValueError('Invalid capital or risk settings')
        if not (1 <= self.fast < self.slow):
            raise ValueError('Require 1 <= fast < slow')

    def run(self, bars: pd.DataFrame, ticker: str = 'SAMPLE') -> dict[str, Any]:
        if not {'Open', 'High', 'Low', 'Close'}.issubset(bars.columns):
            raise ValueError('OHLC bars required')
        df = bars.copy()
        if not df.index.is_monotonic_increasing or df.index.has_duplicates:
            raise ValueError('Index must be strictly chronological and unique')
        for name in ('Open', 'High', 'Low', 'Close'):
            df[name] = pd.to_numeric(df[name], errors='raise')
        if not np.isfinite(df[['Open','High','Low','Close']].to_numpy(dtype=float)).all() or (df[['Open','High','Low','Close']] <= 0).any().any():
            raise ValueError('Prices must be finite positive values')
        if (df['High'] < df[['Open','Close','Low']].max(axis=1)).any() or (df['Low'] > df[['Open','Close']].min(axis=1)).any():
            raise ValueError('Invalid OHLC candle')
        fast_ma = df['Close'].rolling(self.fast).mean()
        slow_ma = df['Close'].rolling(self.slow).mean()
        cash = float(self.initial_cash)
        shares = 0
        stop = None
        trades = []
        equity = []
        pending = None
        entry_price = None
        entry_date = None
        for i in range(len(df)):
            bar = df.iloc[i]
            day = str(df.index[i])
            opened_today = False
            if pending == 'EXIT' and shares:
                px = float(bar['Open'])
                cash += shares * px
                trades.append({'ticker': ticker, 'entry_date': entry_date, 'exit_date': day, 'entry': entry_price, 'exit': px, 'shares': shares, 'pnl': shares * (px - entry_price), 'reason': 'CROSS_DOWN'})
                shares, stop, entry_price, entry_date = 0, None, None, None
            elif pending == 'BUY' and not shares:
                px = float(bar['Open'])
                qty = min(int(cash // px), int((cash * self.risk_fraction) // (px * self.stop_pct)))
                if qty > 0:
                    shares = qty
                    cash -= shares * px
                    stop = px * (1 - self.stop_pct)
                    entry_price, entry_date = px, day
                    opened_today = True
            pending = None
            if shares and not opened_today and float(bar['Low']) <= stop:
                px = min(float(bar['Open']), stop)  # stop gap-through executes at open
                cash += shares * px
                trades.append({'ticker': ticker, 'entry_date': entry_date, 'exit_date': day, 'entry': entry_price, 'exit': px, 'shares': shares, 'pnl': shares * (px - entry_price), 'reason': 'STOP'})
                shares, stop, entry_price, entry_date = 0, None, None, None
            equity.append({'date': day, 'equity': cash + shares * float(bar['Close'])})
            if i and pd.notna(slow_ma.iloc[i-1]) and pd.notna(slow_ma.iloc[i]):
                was_above = fast_ma.iloc[i-1] > slow_ma.iloc[i-1]
                is_above = fast_ma.iloc[i] > slow_ma.iloc[i]
                if not shares and not was_above and is_above:
                    pending = 'BUY'
                elif shares and was_above and not is_above:
                    pending = 'EXIT'
        final_equity = equity[-1]['equity'] if equity else cash
        return {'ticker': ticker, 'initial_equity': self.initial_cash, 'final_equity': final_equity,
                'return_pct': (final_equity / self.initial_cash - 1) * 100,
                'trades': trades, 'equity_curve': equity, 'open_shares': shares,
                'pending_signal': pending, 'execution_assumption': 'next_open; conservative stop gap handling'}
