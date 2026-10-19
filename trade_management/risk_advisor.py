"""Independent, educational long-only risk manager. No broker orders."""
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class PublicTradeManager:
    stop_loss_pct: float = 0.05
    risk_fraction: float = 0.01

    def __post_init__(self):
        if not 0 < self.stop_loss_pct < 1 or not 0 < self.risk_fraction < 1:
            raise ValueError("Percentages must be between zero and one")

    def size(self, equity: float, entry_price: float) -> int:
        if equity <= 0 or entry_price <= 0:
            return 0
        return max(0, min(int(equity*self.risk_fraction/(entry_price*self.stop_loss_pct)), int(equity/entry_price)))

    def evaluate_position(self, position: Mapping[str, Any], bar: Mapping[str, Any]) -> dict[str, Any]:
        entry = float(position.get("entry", position.get("avg_entry_price", 0)))
        close = float(bar["Close"])
        low = float(bar.get("Low", close))
        if entry <= 0 or close <= 0 or low <= 0:
            raise ValueError("Prices must be positive")
        stop = float(position.get("stop") or position.get("current_stop") or entry*(1-self.stop_loss_pct))
        qty = int(position.get("remaining", position.get("open_quantity", 0)))
        stopped = low <= stop
        event = {"type":"STOP", "price":stop, "shares":qty} if stopped and qty > 0 else None
        return {"position_id":position.get("position_id"), "ticker":position.get("ticker"),
                "recommended_action":"STOP" if event else "HOLD",
                "reason":"Fixed percentage stop" if event else "No exit condition",
                "management_bar":int(position.get("management_bar",0)),
                "protected_phase":False, "current_price":close,
                "current_r":(close-entry)/(entry-stop) if entry>stop else None,
                "current_stop":stop, "effective_stop":stop,
                "target_price":None, "open_quantity":qty, "event":event}
