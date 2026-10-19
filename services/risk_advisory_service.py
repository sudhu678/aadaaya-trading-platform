"""Standalone public manager service. Does not write to a broker or database."""
from dataclasses import dataclass, field
from typing import Any
from trade_management.risk_advisor import PublicTradeManager

@dataclass
class PublicManagerService:
    market_data: Any
    manager: PublicTradeManager = field(default_factory=PublicTradeManager)

    @staticmethod
    def normalize_position(position: dict) -> dict:
        entry = float(position.get('entry', position.get('avg_entry_price', 0)))
        stop = position.get('stop') or position.get('current_stop') or position.get('initial_stop')
        return {
            'position_id': position.get('position_id'),
            'ticker': position.get('ticker'),
            'entry': entry,
            'stop': float(stop) if stop is not None else None,
            'remaining': int(position.get('remaining', position.get('open_quantity', 0))),
        }

    def evaluate_position(self, position: dict, bar: Any) -> dict:
        # pandas.Series and plain mappings both expose dictionary-style access.
        return self.manager.evaluate_position(self.normalize_position(position), bar)

    def run_positions(self, positions, mode='TEST') -> list[dict]:
        if str(mode).upper() not in {'TEST', 'BACKTEST', 'LIVE'}:
            raise ValueError('Unsupported mode')
        results = []
        for raw in positions:
            pos = self.normalize_position(raw)
            if not pos['ticker']:
                continue
            bar = self.market_data.latest_daily_bar(pos['ticker'])
            if bar is None:
                continue
            result = self.manager.evaluate_position(pos, bar)
            result['event_advisory'] = None
            results.append(result)
        # Advisory only: never send orders or write persistence, including LIVE.
        return results
