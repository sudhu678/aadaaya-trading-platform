import unittest
from services.market_scanner_service import PublicScannerService
from strategies.sma_crossover import SMACrossoverStrategy

class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.scanner=PublicScannerService(SMACrossoverStrategy(2,3))
    def test_buy_cross(self):
        result=self.scanner.scan_bars("DEMO",{"Close":[10,9,8,12]})
        self.assertEqual(result["action"],"BUY")
    def test_no_cross(self):
        self.assertIsNone(self.scanner.scan_bars("DEMO",{"Close":[10,10,10,10]}))
    def test_universe(self):
        result=self.scanner.scan_universe({"DEMO":{"Close":[10,9,8,12]},"FLAT":{"Close":[10,10,10,10]}})
        self.assertEqual(len(result),1)
    def test_bad_ticker(self):
        with self.assertRaises(ValueError): self.scanner.scan_bars("",{"Close":[10,9,8,12]})
if __name__=='__main__':unittest.main()
