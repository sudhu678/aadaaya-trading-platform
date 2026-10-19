"""Public backtest service entry point. No proprietary historical adapter imports."""
from __future__ import annotations
from typing import Any, Callable
import pandas as pd
from engine.historical_simulator import PublicBacktest
from services.historical_simulation_service import PublicBacktestService
from market_data.yfinance_loader import load_daily_bars


class BacktestService:
    """Compatible method signature; intentionally distinct educational result schema.

    Uses the public Yahoo Finance loader by default; callers can inject a loader.
    No persistence side effects occur here.
    """
    def __init__(self, config: Any = None, *, load_bars: Callable[[str, str, str], pd.DataFrame] | None = None):
        self.config = config
        self._load_bars = load_bars if load_bars is not None else load_daily_bars
        self._engine = PublicBacktest()

    def run_historical_backtest(self, tickers: list[str], start: str, end: str,
                                sector_map: dict[str, str] | None = None) -> dict:
        return PublicBacktestService(self._load_bars, self._engine).run_historical_backtest(
            tickers, start, end, sector_map)

    def get_configuration(self):
        return self.config

    def describe(self) -> dict:
        return {'service': 'BacktestService', 'adapter': 'PublicBacktestService',
                'engine': 'PublicBacktest', 'portfolio_mode': 'independent_tickers',
                'status': 'educational; not production portfolio accounting'}
