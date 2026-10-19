import unittest
from services.manager_service import ManagerService

class Market:
    def latest_daily_bar(self, ticker):
        return {"Close": 96.0, "Low": 94.0}
class Positions:
    def list_positions(self, **kwargs):
        return [{"position_id": 7, "ticker": "ABC", "average_entry_price": 100,
                 "current_stop": 95, "open_quantity": 3}]
class TestManager(unittest.TestCase):
    def test_stop(self):
        out = ManagerService(position_service=Positions(),market_data=Market()).run(portfolio_id=1)
        self.assertEqual(out["recommendations"][0]["recommended_action"], "STOP")
        self.assertEqual(out["recommendations"][0]["event"]["shares"], 3)
    def test_no_write(self):
        m = ManagerService(position_service=Positions(),market_data=Market())
        with self.assertRaises(NotImplementedError): m.run(mode="LIVE",portfolio_id=1)
    def test_no_market_data(self):
        with self.assertRaises(RuntimeError): ManagerService().run_positions([{"entry":100,"ticker":"ABC"}])
if __name__ == "__main__": unittest.main()
