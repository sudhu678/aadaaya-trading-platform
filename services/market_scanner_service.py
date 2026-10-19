"""Public scanner boundary; accepts completed daily bars from any provider.

No proprietary signals, broker integration, database writes or market-data calls.
"""
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Mapping
from strategies.sma_crossover import SMACrossoverStrategy

@dataclass
class PublicScannerService:
    strategy: SMACrossoverStrategy = field(default_factory=SMACrossoverStrategy)

    def scan_bars(self, ticker: str, bars: Any) -> dict | None:
        if not ticker or not isinstance(ticker, str):
            raise ValueError("ticker is required")
        # Accept a pandas DataFrame, a mapping of column arrays, or iterable of OHLCV mappings.
        if hasattr(bars, "columns"):
            closes = list(bars["Close"])
        elif isinstance(bars, Mapping):
            closes = list(bars["Close"])
        else:
            closes = [row["Close"] for row in bars]
        context = SimpleNamespace(ticker=ticker, data={"close_series":closes}, config=self.strategy.get_config())
        signal = self.strategy.generate(context)
        if signal is None:
            return None
        return {"ticker":ticker,"strategy":self.strategy.name,
                "action":signal.values["action"],"price":signal.values["price"],
                "signal":signal}

    def scan_universe(self, bars_by_ticker: Mapping[str, Any]) -> list[dict]:
        results = []
        for ticker, bars in bars_by_ticker.items():
            signal = self.scan_bars(ticker, bars)
            if signal is not None:
                results.append(signal)
        return results
