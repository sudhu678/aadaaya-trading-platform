"""Public strategy registration. Add independent community strategies here."""
from .sma_crossover import SMACrossoverStrategy
STRATEGY_REGISTRY = {"SMA Crossover": SMACrossoverStrategy()}
