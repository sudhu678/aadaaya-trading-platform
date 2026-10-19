"""Public, injectable historical backtest service; no proprietary dependencies."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
import pandas as pd
from engine.historical_simulator import PublicBacktest

@dataclass
class PublicBacktestService:
    """Use an injected OHLC data loader; keep networking outside the engine."""
    load_bars: Callable[[str, str, str], pd.DataFrame]
    engine: PublicBacktest = field(default_factory=PublicBacktest)

    def run_historical_backtest(self, tickers: list[str], start: str, end: str,
                                sector_map: dict[str, str] | None = None) -> dict:
        if not tickers or not all(isinstance(t, str) and t.strip() for t in tickers):
            raise ValueError('At least one valid ticker required')
        start_date, end_date = pd.Timestamp(start), pd.Timestamp(end)
        if start_date >= end_date:
            raise ValueError('Start must precede end')
        results = {}
        for ticker in dict.fromkeys(tickers):
            bars = self.load_bars(ticker, start, end)
            if not isinstance(bars, pd.DataFrame):
                raise TypeError('Market data loader must return a DataFrame')
            results[ticker] = self.engine.run(bars, ticker=ticker)
        return {'strategy': 'SMA_CROSSOVER_EXAMPLE', 'results': results,
                'initial_equity_per_ticker': self.engine.initial_cash,
                'note': 'Independent per-ticker educational simulations; not a shared portfolio backtest.'}
