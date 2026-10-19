"""Public registry-backed strategy routing."""
from .registry import STRATEGY_REGISTRY

def available_strategies():
    return [name for name, strategy in STRATEGY_REGISTRY.items()
            if strategy.get_config().get("ENABLED", True)]

def get_strategy(name):
    return STRATEGY_REGISTRY.get(name)

def generate_strategy_signal(name, context):
    strategy = get_strategy(name)
    if strategy is None:
        raise ValueError(f"Unknown strategy: {name}")
    if not strategy.get_config().get("ENABLED", True):
        return None
    context.config = strategy.get_config()
    return strategy.generate(context)
