"""Minimal public strategy interface; no proprietary gates or scoring."""
from abc import ABC, abstractmethod

class StrategyBase(ABC):
    name = "BASE"

    @abstractmethod
    def generate(self, context):
        """Return an educational public signal or None."""
        raise NotImplementedError
