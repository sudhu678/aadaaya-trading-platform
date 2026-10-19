import unittest
from types import SimpleNamespace
from strategies.router import available_strategies, get_strategy
from services.market_scanner_service import PublicScannerService
from trade_management.risk_advisor import PublicTradeManager

class IntegrationTests(unittest.TestCase):
    def test_registry(self):
        self.assertEqual(available_strategies(), ["SMA Crossover"])
        self.assertIsNotNone(get_strategy("SMA Crossover"))
    def test_scanner_no_signal_flat_market(self):
        self.assertIsNone(PublicScannerService().scan_bars("TEST", {"Close":[100]*60}))
    def test_manager_stop(self):
        out=PublicTradeManager().evaluate_position({"ticker":"TEST","entry":100,"remaining":2},{"Close":96,"Low":94})
        self.assertEqual(out["recommended_action"],"STOP")
    def test_manager_advisory_only(self):
        out=PublicTradeManager().evaluate_position({"ticker":"TEST","entry":100,"remaining":2},{"Close":100,"Low":99})
        self.assertEqual(out["recommended_action"],"HOLD")
if __name__ == "__main__": unittest.main()
