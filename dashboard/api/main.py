"""Standalone public dashboard API composition. No proprietary source imports."""
from fastapi import FastAPI, HTTPException
from .scanner_manager_api import router as operations_router
from .trades_api import router as trades_router
app=FastAPI(title='Aadaaya Trading Platform — Public API', version='0.1.0')
app.include_router(operations_router)
app.include_router(trades_router)
from .portfolio_api import router as portfolio_router
app.include_router(portfolio_router)
@app.get('/api/health')
def health(): return {'status':'ok','edition':'public','execution':'advisory-only'}
@app.get('/api/backtests')
def backtests(): return []
@app.get('/api/backtests/{report_id}/sheets',status_code=410)
def sheets(report_id:str): raise HTTPException(410,'Private historical reports are not distributed')
@app.get('/api/backtests/{report_id}/preview',status_code=410)
def preview(report_id:str): raise HTTPException(410,'Private historical reports are not distributed')

from .backtest_routes import router as public_backtest_router
app.include_router(public_backtest_router)
