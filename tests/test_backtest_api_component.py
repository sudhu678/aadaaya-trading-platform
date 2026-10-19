import unittest
from datetime import date, timedelta
from fastapi.testclient import TestClient
import pandas as pd
from dashboard.api.main import app
from dashboard.api.backtest_routes import get_loader
from engine.historical_simulator import PublicBacktest

class BacktestAPITests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def loader(ticker, start, end):
            self.calls.append(ticker)
            index = pd.date_range('2025-01-01', periods=100, freq='B')
            close = [100.0 + i * 0.2 for i in range(100)]
            return pd.DataFrame({'Open': close, 'High': [x+1 for x in close],
                                 'Low': [x-1 for x in close], 'Close': close}, index=index)
        app.dependency_overrides[get_loader] = lambda: loader
        self.client = TestClient(app)
        self.body = {'tickers':['ABC'], 'start':'2025-01-01', 'end':'2025-06-01'}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_run_without_network(self):
        r=self.client.post('/api/public-backtest/run',json=self.body)
        self.assertEqual(r.status_code,200,r.text)
        self.assertTrue(r.json()['advisory_only'])
        self.assertIn('ABC',r.json()['results'])
        self.assertEqual(self.calls,['ABC'])

    def test_invalid_symbols(self):
        self.assertEqual(self.client.post('/api/public-backtest/run',json={**self.body,'tickers':['../secret']}).status_code,422)

    def test_duplicate_symbols(self):
        self.assertEqual(self.client.post('/api/public-backtest/run',json={**self.body,'tickers':['abc','ABC']}).status_code,422)

    def test_invalid_window(self):
        self.assertEqual(self.client.post('/api/public-backtest/run',json={**self.body,'fast':50,'slow':20}).status_code,422)

    def test_future_dates(self):
        self.assertEqual(self.client.post('/api/public-backtest/run',json={**self.body,'end':(date.today()+timedelta(days=2)).isoformat()}).status_code,422)

    def test_reject_infinite_price(self):
        bars=pd.DataFrame({'Open':[100,float('inf')],'High':[101,float('inf')], 'Low':[99,99], 'Close':[100,100]},index=pd.date_range('2025-01-01',periods=2))
        with self.assertRaises(ValueError): PublicBacktest().run(bars)

if __name__=='__main__': unittest.main()
