"""Compatibility boundary for a public educational scanner.

Accepts externally supplied daily bars; deliberately does not import any
private scanner, strategy, ranking, or execution implementation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Any
import pandas as pd
from services.market_scanner_service import PublicScannerService

COLUMNS = ["Ticker", "strategy_name", "entry_price", "stop_loss", "Shares", "Risk $", "Runner Target", "Quality Score", "Composite Rank", "Action"]

@dataclass
class PublicDataFrameScanner:
    bars_provider: Any
    config: dict = field(default_factory=lambda: {"ACCOUNT_EQUITY": 10000.0})
    scanner: PublicScannerService = field(default_factory=PublicScannerService)

    def scan(self, tickers: list[str] | None = None) -> pd.DataFrame:
        if tickers is None:
            raise ValueError("Pass a ticker list explicitly; no private universe defaults")
        rows = []
        for ticker in tickers:
            bars = self.bars_provider(ticker)
            if bars is None or len(bars) == 0:
                continue
            result = self.scanner.scan_bars(ticker, bars)
            if result is None:
                continue
            price = float(result["price"])
            rows.append({"Ticker": ticker, "strategy_name": result["strategy"],
                         "entry_price": price, "stop_loss": None, "Shares": None,
                         "Risk $": None, "Runner Target": None,
                         "Quality Score": None, "Composite Rank": None,
                         "Action": result["action"]})
        return pd.DataFrame(rows, columns=COLUMNS)
