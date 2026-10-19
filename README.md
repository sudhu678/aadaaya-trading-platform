# Aadaaya Trading Platform

© 2026 Aadaaya Trading Platform  
License: MIT — see `LICENSE`.

Aadaaya is an educational trading research dashboard that you can extend with **your own trading strategies and trade-management rules**. The included example uses a 20/50-day simple moving average (SMA) crossover and a fixed-percentage stop-loss advisor. The application is **not a live trading or brokerage execution system**.

<img width="1912" height="948" alt="image" src="https://github.com/user-attachments/assets/bb309447-5e8b-495e-a0cb-6a8d374be6c0" />


> **Important integration boundary:** Adding a strategy to the registry makes it available to the strategy router, but does **not** automatically connect it to the scanner UI, historical backtest engine, or trade manager. Those paths currently use the included example directly. The instructions below distinguish a working extension point from additional integration work.

## 1. Requirements and startup

- Python 3.10+ recommended; Node.js and npm for the React UI.
- Internet access for Yahoo Finance market-data downloads.
- Windows PowerShell: run scripts with the `./` or `.\` prefix, not just their filenames.

**Windows — easiest startup:** Open two PowerShell windows at the repository root:

```powershell
.\start-backend.bat
```

```powershell
.\start-frontend.bat
```

The backend normally listens at `http://127.0.0.1:8000` (API docs: `http://127.0.0.1:8000/docs`); Vite prints the frontend URL, usually `http://localhost:5173`.

**Manual setup (Windows):**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.create_demo_db --out demo_positions.sqlite3
$env:TRADING_DB_PATH = (Resolve-Path demo_positions.sqlite3).Path
python run_dashboard_api.py
```

In a second terminal:

```powershell
cd dashboard/ui
npm install
npm run dev
```

**macOS/Linux:** Run `./start-backend.sh` and `./start-frontend.sh` in separate terminals, or use the equivalent manual setup (`python3 -m venv .venv`, `source .venv/bin/activate`). The demo database contains synthetic records only. Never commit real trading databases, credentials, or personal data.

## 2. Understand the extension points

| Purpose | Source file | Current behavior |
| --- | --- | --- |
| Strategy interface | `strategies/strategy_base.py` | Defines the `generate(context)` method |
| Strategy inputs and output | `strategies/strategy_context.py`, `strategies/strategy_signal.py` | Dataclasses for context and signal |
| Included example strategy | `strategies/sma_crossover.py` | Produces `BUY` and `EXIT` crossover signals |
| Strategy registration | `strategies/registry.py` | Maps display names to strategy instances |
| Strategy routing | `strategies/router.py` | Looks up a registered strategy and calls it |
| Scanner calculation | `services/market_scanner_service.py` | Currently instantiates the SMA example directly |
| Scanner and manager HTTP jobs | `dashboard/api/scanner_manager_api.py` | Currently restricts scanner requests to `SMA_CROSSOVER` |
| Historical backtest engine | `engine/historical_simulator.py` | Implements SMA signals internally, independently of the registry |
| Historical backtest API | `dashboard/api/backtest_routes.py` | Accepts SMA windows, stop and risk parameters |
| Example trade manager | `trade_management/risk_advisor.py` | Fixed-percentage stop recommendations only |
| Manager orchestration | `services/manager_service.py` | Calls an injected or default manager object |
| Manager API | `dashboard/api/scanner_manager_api.py` | Currently instantiates the example manager directly |

Use a **new file** for your own strategy or manager. Avoid modifying the included example until your replacement is tested.

## 3. Implement your first strategy

A strategy receives a `StrategyContext` containing a ticker and a `data` dictionary. It returns a `StrategySignal` or `None` when no action is indicated.

Create `strategies/price_momentum.py`:

```python
from strategies.strategy_base import StrategyBase
from strategies.strategy_signal import StrategySignal


class PriceMomentumStrategy(StrategyBase):
    name = "Price Momentum"

    def __init__(self, lookback=10):
        if lookback < 1:
            raise ValueError("lookback must be positive")
        self.lookback = lookback

    def get_config(self):
        return {"ENABLED": True, "LOOKBACK": self.lookback}

    def generate(self, context):
        closes = context.data.get("close_series", [])
        if len(closes) < self.lookback + 1:
            return None

        # Illustrative rule: signal only on a fresh breakout above
        # the previous N completed closes. No future data is used.
        previous_high = max(closes[-self.lookback - 1:-1])
        latest = float(closes[-1])
        if latest <= previous_high:
            return None

        return StrategySignal(
            ticker=context.ticker or "",
            strategy=self.name,
            values={"action": "BUY", "price": latest},
        )
```

This is an intentionally simple educational example, **not a validated trading edge**. It illustrates the interface and uses only information available at the end of the latest completed bar.

### Register the strategy

Edit `strategies/registry.py`:

```python
from .sma_crossover import SMACrossoverStrategy
from .price_momentum import PriceMomentumStrategy

STRATEGY_REGISTRY = {
    "SMA Crossover": SMACrossoverStrategy(),
    "Price Momentum": PriceMomentumStrategy(lookback=10),
}
```

The current router checks `get_config()["ENABLED"]` and passes the strategy's configuration into the context. Implementing `get_config()` is therefore required for compatibility with the current router, even though the abstract base only declares `generate()`.

### Verify strategy routing

From the repository root:

```powershell
python -c "from strategies.router import available_strategies; print(available_strategies())"
```

For a quick functional check:

```python
from strategies.router import generate_strategy_signal
from strategies.strategy_context import StrategyContext

context = StrategyContext(
    ticker="DEMO",
    data={"close_series": [10.0] * 11 + [11.0]},
    config={},
)
signal = generate_strategy_signal("Price Momentum", context)
print(signal)
```

**What this enables:** Programmatic routing through `strategies/router.py`. **What it does not yet enable:** Selecting the new strategy in the scanner UI or backtest API.

## 4. Connect your strategy to the scanner

The included scanner (`services/market_scanner_service.py`) currently creates an `SMACrossoverStrategy` directly. For a one-strategy experiment, instantiate your class instead and pass it into the scanner:

```python
from services.market_scanner_service import PublicScannerService
from strategies.price_momentum import PriceMomentumStrategy

scanner = PublicScannerService(strategy=PriceMomentumStrategy())
# bars is a DataFrame with a "Close" column, or another supported bar format.
result = scanner.scan_bars("DEMO", bars)
```

The scanner's dataclass type annotation currently names `SMACrossoverStrategy`; to support arbitrary strategies cleanly, change that annotation to a shared strategy interface or protocol. The scanner expects a `get_config()` method and a signal with `values["action"]` and `values["price"]`.

To make the strategy selectable **through the existing HTTP scanner and UI**, additional changes are necessary:

1. Update `ScanRequest.strategies` validation in `dashboard/api/scanner_manager_api.py`. The endpoint currently accepts only `SMA_CROSSOVER`.
2. Update its `_scan()` function to instantiate or route to the requested strategy rather than always using the SMA scanner.
3. Preserve the scanner response fields consumed by the UI (ticker, strategy name, action and price).
4. Add a strategy selector in `dashboard/ui/src/main.tsx` if you want users to choose it in the interface.
5. Add tests for unsupported strategy names, insufficient history and missing data.

Do not simply remove the HTTP allowlist without implementing the corresponding strategy selection and validation.

## 5. Connect your strategy to historical backtesting

The built-in historical engine (`engine/historical_simulator.py`) calculates SMA crossover signals itself. **Registering a new strategy does not change backtest results.** The HTTP API (`dashboard/api/backtest_routes.py`) likewise exposes SMA-specific `fast` and `slow` settings.

For a new strategy, you will need to implement or extend a simulation engine that:

- Calls your strategy on **completed historical bars only**, without future data.
- Enters at the next eligible bar (or clearly documents another execution assumption).
- Tracks cash, position quantities, entries, exits and an equity curve.
- Applies explicit stops, fees, slippage and gap assumptions as needed.
- Produces the result schema expected by the reporting and dashboard code.
- Exposes and validates a strategy identifier and its parameters in the API.

A convenient starting point is to study `engine/historical_simulator.py` and `services/historical_simulation_service.py`, then add a separate engine for your strategy. Keep the sample engine unchanged for regression comparison.

The current backtest is **independent per ticker**; it is not a shared-capital, portfolio-level simulation. It does not fully account for commissions, slippage, corporate actions or production-grade execution.

## 6. Implement your own trade manager

Trade management decides what to recommend **for an already-open position**. It is distinct from a strategy's entry signals. The included manager in `trade_management/risk_advisor.py` provides a fixed-percentage stop-loss advisory and a simple position-size helper. It does not submit orders.

Create `trade_management/trailing_stop_advisor.py`:

```python
class TrailingStopAdvisor:
    """Example advisory manager; no orders or persistence."""

    def __init__(self, trail_pct=0.05):
        if not 0 < trail_pct < 1:
            raise ValueError("trail_pct must be between 0 and 1")
        self.trail_pct = trail_pct

    def evaluate_position(self, position, bar):
        entry = float(position["entry"])
        close = float(bar["Close"])
        low = float(bar.get("Low", close))
        quantity = int(position.get("open_quantity", 0))
        prior_stop = position.get("current_stop")
        # This example trails from the *completed close*, so a newly
        # calculated stop is an advisory for the NEXT session only.
        proposed_stop = close * (1 - self.trail_pct)
        next_stop = max(float(prior_stop), proposed_stop) if prior_stop is not None else proposed_stop
        existing_stop_hit = prior_stop is not None and low <= float(prior_stop)
        return {
            "position_id": position.get("position_id"),
            "ticker": position.get("ticker"),
            "recommended_action": "STOP" if existing_stop_hit and quantity else "HOLD",
            "reason": "Prior stop touched" if existing_stop_hit else "Trailing stop advisory",
            "current_price": close,
            "current_stop": float(prior_stop) if prior_stop is not None else None,
            "effective_stop": next_stop,
            "open_quantity": quantity,
            "event": None,  # No order is created.
        }
```

**Timing matters:** Do not use the same day's closing price to retroactively trigger a newly raised stop earlier that day. The example checks the *previously established* stop against today's low, and proposes an updated stop for future use. A real execution model must also handle opening gaps and intraday ordering.

### Try the manager without changing the API

```python
from trade_management.trailing_stop_advisor import TrailingStopAdvisor

advisor = TrailingStopAdvisor(trail_pct=0.05)
result = advisor.evaluate_position(
    {"position_id": 1, "ticker": "DEMO", "entry": 100.0,
     "open_quantity": 10, "current_stop": 94.0},
    {"Close": 105.0, "Low": 102.0},
)
print(result)
```

For service-level integration, `services/manager_service.py` accepts an injected `manager` object exposing `evaluate_position(position, bar)`. The existing HTTP manager job, however, constructs `PublicTradeManager` directly in `dashboard/api/scanner_manager_api.py`. To use your manager in the UI, wire it into that endpoint and ensure the returned fields match the UI's expectations. Keep the endpoint **advisory-only** and preserve read-only database access.

The standalone `services/risk_advisory_service.py` is a second service path; choose one integration path deliberately rather than assuming changing one updates every caller.

## 7. Test your changes

Run the existing regression suite from the repository root:

```powershell
python -m pytest -q
```

Add focused tests for your own logic, including no-signal cases, invalid inputs, insufficient lookback, missing bars, price gaps, and prevention of look-ahead bias. For trade management, test unchanged stops, tightened stops, stops touched by the previous bar's low, and zero-quantity positions.

Before packaging or publishing:

```powershell
python scripts/release_audit.py
```

The automated audit is a safety check, **not a guarantee** that a repository is free of proprietary code or secrets. Manually review the complete diff, dependencies, sample data, and licensing. Do not include `.env` files, API keys, real SQLite databases, private research, or strategy code you do not have permission to distribute.

## 8. Current limitations and safety

- Educational use and research only; not investment advice.
- No live brokerage integration, order placement, or persistent trade-manager decisions.
- The included scanner and historical engine use the sample SMA strategy unless explicitly modified.
- Market-data downloads require a network connection and may fail or be delayed.
- The eight-screen UI has not yet been certified by a complete browser end-to-end test.
- Historical portfolio accounting and performance metrics must not be treated as verified production results.

See `CONTRIBUTING.md`, `SECURITY.md`, and `DISCLAIMER.md` for additional guidance.
