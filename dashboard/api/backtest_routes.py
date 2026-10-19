"""Bounded educational historical simulation API. Never places orders."""
from __future__ import annotations
from datetime import date
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reporting.backtest_excel_report import build_xlsx_report
from pydantic import BaseModel, Field, field_validator
from market_data.yfinance_loader import load_daily_bars
from services.historical_simulation_service import PublicBacktestService
from engine.historical_simulator import PublicBacktest

router = APIRouter(prefix="/api/public-backtest", tags=["Public historical backtest"])
_TICKER = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,11}\Z")

class BacktestRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=10)
    start: date
    end: date
    initial_cash: float = Field(default=10000.0, gt=0, le=1_000_000_000)
    stop_pct: float = Field(default=0.05, gt=0, lt=1)
    risk_fraction: float = Field(default=0.01, gt=0, le=1)
    fast: int = Field(default=20, ge=1, le=200)
    slow: int = Field(default=50, ge=2, le=500)

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, value):
        symbols = [v.strip().upper() for v in value]
        if any(not _TICKER.fullmatch(v) for v in symbols) or len(set(symbols)) != len(symbols):
            raise ValueError("Tickers must be unique valid symbols")
        return symbols


def get_loader():
    return load_daily_bars

def execute_backtest(request: BacktestRequest, loader):
    if request.start >= request.end:
        raise HTTPException(422, "start must precede end")
    if request.end > date.today():
        raise HTTPException(422, "end cannot be in the future")
    if (request.end - request.start).days > 365 * 20:
        raise HTTPException(422, "Date range exceeds 20 years")
    if request.fast >= request.slow:
        raise HTTPException(422, "fast must be less than slow")
    engine = PublicBacktest(initial_cash=request.initial_cash, stop_pct=request.stop_pct,
                            risk_fraction=request.risk_fraction, fast=request.fast, slow=request.slow)
    service = PublicBacktestService(load_bars=loader, engine=engine)
    try:
        output = service.run_historical_backtest(request.tickers, request.start.isoformat(), request.end.isoformat())
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        # Do not expose internal paths or provider secrets to API clients.
        raise HTTPException(503, "Historical market data unavailable") from exc
    output["advisory_only"] = True
    output["disclaimer"] = "Educational simulation; no order execution, slippage, commissions or corporate-action reconciliation."
    return output


@router.post("/run")
def run_backtest(request: BacktestRequest, loader=Depends(get_loader)):
    return execute_backtest(request, loader)


@router.post("/export")
def export_backtest(request: BacktestRequest, loader=Depends(get_loader)):
    result = execute_backtest(request, loader)
    try:
        payload = build_xlsx_report(result)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return StreamingResponse(
        iter([payload]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=aadaaya_public_backtest.xlsx",
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
