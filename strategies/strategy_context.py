"""Generic context for educational strategy demonstrations."""
from dataclasses import dataclass
from typing import Any

@dataclass
class StrategyContext:
    data: dict[str, Any]
    config: Any
    ticker: str | None = None
    date: Any = None
