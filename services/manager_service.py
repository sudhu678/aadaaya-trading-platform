"""Public advisory manager service; intentionally no proprietary rules or order execution."""
from dataclasses import dataclass, field
from typing import Any
from trade_management.risk_advisor import PublicTradeManager

@dataclass
class ManagerService:
    position_service: object | None = None
    persistence: object | None = None
    market_data: object | None = None
    report_service: object | None = None
    advisory_provider: object | None = None
    advisory_enabled: bool = False
    manager: PublicTradeManager = field(default_factory=PublicTradeManager)

    @staticmethod
    def normalize_position(position: dict[str, Any]) -> dict[str, Any]:
        def pick(*keys, default=None):
            return next((position[k] for k in keys if position.get(k) is not None), default)
        entry = pick("entry", "average_entry_price", "avg_entry_price", "entry_price")
        qty = pick("open_quantity", "remaining", "quantity", "shares", default=0)
        if entry is None:
            raise ValueError("Position entry price required")
        return {"position_id": pick("position_id"), "portfolio_id": pick("portfolio_id"),
                "ticker": pick("ticker"), "entry": float(entry),
                "stop": pick("current_stop", "stop", "stop_price"),
                "open_quantity": int(qty), "management_bar": int(pick("management_bar", default=0))}

    def evaluate_position(self, position: dict, bar: Any) -> dict:
        result = self.manager.evaluate_position(self.normalize_position(position), bar)
        result["event_advisory"] = None
        return result

    def run_positions(self, positions, mode="TEST"):
        mode = mode.upper()
        if mode not in {"TEST", "BACKTEST"}:
            raise NotImplementedError("Public manager is advisory-only; LIVE persistence is not implemented")
        if self.market_data is None:
            raise RuntimeError("A market_data provider with latest_daily_bar(ticker) is required")
        results = []
        for raw in positions:
            position = self.normalize_position(raw)
            bar = self.market_data.latest_daily_bar(position["ticker"])
            if bar is not None:
                results.append(self.evaluate_position(position, bar))
        return results

    def run(self, mode="TEST", portfolio_id=None):
        if self.position_service is None:
            raise RuntimeError("PositionTrackingService required")
        if portfolio_id is None:
            raise ValueError("portfolio_id required")
        positions = self.position_service.list_positions(portfolio_id=portfolio_id, status="OPEN")
        recommendations = self.run_positions(positions, mode=mode)
        report = (self.report_service.create_manager_report(recommendations, mode=mode)
                  if self.report_service is not None else None)
        return {"recommendations": recommendations, "report": report}
