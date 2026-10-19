import unittest
from unittest.mock import patch
import pandas as pd
from services.backtest_service import BacktestService
from market_data.yfinance_loader import load_daily_bars

class MarketWiringTests(unittest.TestCase):
    def test_default_loader_is_public(self):
        self.assertIs(BacktestService()._load_bars, load_daily_bars)
    def test_injected_loader(self):
        bars = pd.DataFrame({'Open':[10]*70,'High':[11]*70,'Low':[9]*70,'Close':[10]*70,'Volume':[100]*70})
        output = BacktestService(load_bars=lambda t,s,e: bars).run_historical_backtest(['ABC'],'2025-01-01','2025-05-01')
        self.assertIn('ABC',output['results'])
    def test_empty_ticker(self):
        with self.assertRaises(ValueError):load_daily_bars('','2025-01-01','2025-02-01')
    def test_invalid_dates(self):
        with self.assertRaises(ValueError):load_daily_bars('ABC','2025-02-01','2025-01-01')

if __name__=='__main__':unittest.main()
