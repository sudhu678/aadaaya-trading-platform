"""Simple public signal payload."""
from dataclasses import dataclass
from typing import Any

@dataclass
class StrategySignal:
    ticker: str
    strategy: str
    values: dict[str, Any]
