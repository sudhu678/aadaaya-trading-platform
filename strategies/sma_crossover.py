"""Educational moving-average crossover on completed daily closes."""
from math import isfinite
from .strategy_base import StrategyBase
from .strategy_signal import StrategySignal

class SMACrossoverStrategy(StrategyBase):
    name = "SMA Crossover"
    def __init__(self, short_window=20, long_window=50):
        if not (1 <= short_window < long_window):
            raise ValueError("Expected 1 <= short_window < long_window")
        self.short_window = short_window
        self.long_window = long_window

    def get_config(self):
        return {"ENABLED": True, "SHORT_WINDOW": self.short_window,
                "LONG_WINDOW": self.long_window}

    def quality_score(self, signal, features):
        return 50.0  # neutral illustrative score, not a predictive model

    def generate(self, context):
        series = context.data.get("close_series")
        if series is None:
            return None
        try:
            closes = [float(x) for x in series]
        except (TypeError, ValueError):
            return None
        long = self.long_window
        short = self.short_window
        if len(closes) < long + 1 or not all(map(isfinite, closes[-long-1:])):
            return None
        prev_short = sum(closes[-short-1:-1]) / short
        prev_long = sum(closes[-long-1:-1]) / long
        curr_short = sum(closes[-short:]) / short
        curr_long = sum(closes[-long:]) / long
        direction = ("BUY" if prev_short <= prev_long and curr_short > curr_long else
                     "EXIT" if prev_short >= prev_long and curr_short < curr_long else None)
        if direction is None:
            return None
        return StrategySignal(ticker=context.ticker or "", strategy=self.name,
                              values={"action": direction, "price": closes[-1],
                                      "short_sma": curr_short, "long_sma": curr_long})
