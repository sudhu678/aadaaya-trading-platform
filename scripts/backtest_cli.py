"""Standalone CLI for public, advisory-only SMA crossover backtests."""
from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path
import sys
from dashboard.api.backtest_routes import BacktestRequest, execute_backtest
from market_data.yfinance_loader import load_daily_bars
from reporting.backtest_excel_report import build_xlsx_report
from reporting.backtest_json_report import build_json_report

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Educational SMA crossover historical backtest (no order execution)")
    parser.add_argument('--tickers', nargs='+', required=True)
    parser.add_argument('--start', required=True, type=date.fromisoformat)
    parser.add_argument('--end', required=True, type=date.fromisoformat)
    parser.add_argument('--initial-cash', type=float, default=10000.0)
    parser.add_argument('--fast', type=int, default=20)
    parser.add_argument('--slow', type=int, default=50)
    parser.add_argument('--stop-pct', type=float, default=0.05)
    parser.add_argument('--risk-fraction', type=float, default=0.01)
    parser.add_argument('--format', choices=('json', 'xlsx'), default='xlsx')
    parser.add_argument('--out', required=True, help='Output report file path')
    return parser.parse_args(argv)

def run(argv=None, loader=load_daily_bars):
    args = parse_args(argv)
    expected_suffix = '.' + args.format
    output = Path(args.out)
    if output.suffix.lower() != expected_suffix:
        raise ValueError('Output filename must end with ' + expected_suffix)
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing report')
    request = BacktestRequest(tickers=args.tickers, start=args.start, end=args.end,
        initial_cash=args.initial_cash, fast=args.fast, slow=args.slow,
        stop_pct=args.stop_pct, risk_fraction=args.risk_fraction)
    result = execute_backtest(request, loader)
    payload = build_json_report(result) if args.format == 'json' else build_xlsx_report(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as file: file.write(payload)
    return output

def main():
    try:
        output = run()
    except Exception as exc:
        print(f'Backtest failed: {exc}', file=sys.stderr)
        return 1
    print(f'Educational report written to {output}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
