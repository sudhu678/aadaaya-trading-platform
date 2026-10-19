"""Public, advisory-only operations API compatible with dashboard job polling."""
from __future__ import annotations
import re, sqlite3, os, threading, uuid
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/operations", tags=["Public operations"])
_pool = ThreadPoolExecutor(max_workers=2)
_lock = threading.Lock()
_jobs = {}
SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,11}$")

class ScanRequest(BaseModel):
    universe: str = "CUSTOM"
    tickers: str = ""
    strategies: list[str] = Field(default_factory=lambda: ["SMA_CROSSOVER"])
    equity: float = Field(default=10000.0, gt=0)
    top_n: int = Field(default=10, ge=1, le=500)
    db_write_mode: str = "OFF"
    portfolio_id: int | None = None
    confirm_live_write: bool = False

class ManagerRequest(BaseModel):
    portfolio_id: int = Field(ge=1)
    db_mode: str = "TEST"

def _work(job_id, fn, *args):
    with _lock: _jobs[job_id]["status"] = "running"
    try:
        rows, warning = fn(*args)
        with _lock:
            _jobs[job_id].update(status="completed", rows=rows, count=len(rows),
                                 warning=warning, report_ready=False)
    except Exception as exc:
        with _lock: _jobs[job_id].update(status="failed", error=f"{type(exc).__name__}: {exc}")

def _submit(kind, fn, *args):
    with _lock:
        if sum(j["status"] in ("queued", "running") for j in _jobs.values()) >= 2:
            raise HTTPException(409, "Two operations already running")
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {"id":job_id,"kind":kind,"status":"queued", "rows":[],"count":0,"error":None}
    _pool.submit(_work, job_id, fn, *args)
    return {"id":job_id,"status":"queued"}

def _scan(tickers, top_n):
    from market_data.yfinance_loader import load_daily_bars
    from services.market_scanner_service import PublicScannerService
    end = date.today()
    start = end - timedelta(days=400)
    scanner = PublicScannerService()
    rows, failures = [], []
    for ticker in tickers:
        try:
            bars = load_daily_bars(ticker, start.isoformat(), end.isoformat())
            if bars is None or bars.empty:
                failures.append(ticker)
                continue
            signal = scanner.scan_bars(ticker, bars)
            if signal:
                rows.append({"Ticker":ticker,"Assigned Strategy":"SMA Crossover",
                             "Strategy":"SMA Crossover","Action":signal["action"],
                             "Entry Price":float(signal["price"]),
                             "ticker":ticker,"strategy_name":"SMA Crossover",
                             "action":signal["action"],"price":float(signal["price"])})
        except Exception:
            failures.append(ticker)
    warning = f"No data or scanning failed for {len(failures)} ticker(s)" if failures else None
    return rows[:top_n], warning

def _manager(portfolio_id):
    from market_data.yfinance_loader import load_daily_bars
    from trade_management.risk_advisor import PublicTradeManager
    path = Path(os.getenv("TRADING_DB_PATH", "")).expanduser()
    if not os.getenv("TRADING_DB_PATH") or not path.is_file():
        raise RuntimeError("Configure TRADING_DB_PATH to an existing SQLite database")
    with sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True) as con:
        con.row_factory=sqlite3.Row
        positions = [dict(r) for r in con.execute(
            "SELECT * FROM positions WHERE portfolio_id=? AND status='OPEN' LIMIT 500",(portfolio_id,))]
    manager=PublicTradeManager()
    rows=[]; failures=[]
    end=date.today();start=end-timedelta(days=14)
    for p in positions:
        ticker=str(p.get("ticker") or p.get("symbol") or "").upper()
        if not SYMBOL.fullmatch(ticker):
            failures.append(ticker);continue
        try:
            bars=load_daily_bars(ticker,start.isoformat(),end.isoformat())
            if bars is None or bars.empty: failures.append(ticker);continue
            bar=bars.iloc[-1]
            entry=next((p[k] for k in ("average_entry_price","avg_entry_price","entry_price","entry") if p.get(k) is not None),None)
            if entry is None: failures.append(ticker);continue
            normalized={"position_id":p.get("position_id"),"ticker":ticker,"entry":float(entry),
                "open_quantity":int(p.get("open_quantity") or p.get("quantity") or 0),
                "current_stop":p.get("current_stop") or p.get("stop_price")}
            rows.append(manager.evaluate_position(normalized,{"Close":float(bar["Close"]),"Low":float(bar["Low"])}))
        except Exception: failures.append(ticker)
    warning=f"Unable to evaluate {len(failures)} position(s)" if failures else None
    return rows, warning

@router.post("/scanner/runs")
def start_scan(request: ScanRequest):
    if request.db_write_mode.upper() != "OFF":
        raise HTTPException(422,"Public scanner is read-only; database writes are disabled")
    if request.universe.upper() != "CUSTOM":
        raise HTTPException(422,"Public scanner currently supports CUSTOM tickers only")
    if not request.strategies or set(s.upper() for s in request.strategies) != {"SMA_CROSSOVER"}:
        raise HTTPException(422,"Only SMA_CROSSOVER is supported")
    tickers=list(dict.fromkeys(x.strip().upper() for x in request.tickers.replace("\n",",").split(",") if x.strip()))
    if not 1 <= len(tickers) <= 100 or any(not SYMBOL.fullmatch(t) for t in tickers):
        raise HTTPException(422,"Provide 1–100 valid ticker symbols")
    return _submit("scanner",_scan,tickers,request.top_n)

@router.post("/manager/runs")
def start_manager(request: ManagerRequest):
    if request.db_mode.upper() != "TEST":
        raise HTTPException(422,"Public manager supports advisory TEST mode only")
    return _submit("manager",_manager,request.portfolio_id)

@router.get("/runs/{job_id}")
def get_run(job_id: str):
    with _lock:
        if job_id not in _jobs: raise HTTPException(404,"Job not found")
        return dict(_jobs[job_id])

@router.get("/scanner/runs/{job_id}/excel")
def download_scanner_excel(job_id: str):
    raise HTTPException(409,"Excel export is not available in the public operations API")

@router.delete("/scanner/runs/{job_id}/excel")
def delete_scanner_excel(job_id: str):
    raise HTTPException(404,"No generated Excel report exists")
