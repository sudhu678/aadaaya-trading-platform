"""Public Yahoo Finance daily OHLCV loader; no private cache or credentials."""
from __future__ import annotations
import pandas as pd
import os
from market_data.sqlite_cache import DailyBarCache


def load_daily_bars(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV; caller's end date is inclusive, unlike yfinance's end."""
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError('A nonempty ticker is required')
    begin, finish = pd.Timestamp(start), pd.Timestamp(end)
    if begin >= finish:
        raise ValueError('Start date must precede end date')
    cache_path = os.environ.get('PUBLIC_MARKET_CACHE_PATH', '').strip()
    cache = DailyBarCache(cache_path) if cache_path else None
    if cache is not None:
        cached = cache.read(ticker.strip().upper(), begin.strftime('%Y-%m-%d'), finish.strftime('%Y-%m-%d'))
        # Only return from cache if every weekday in range is represented. Market
        # holidays make this conservative: fetch again rather than claim completeness.
        weekdays = pd.date_range(begin.normalize(), finish.normalize(), freq='B')
        if len(weekdays) and set(weekdays).issubset(set(cached.index.normalize())):
            return cached
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError('Install yfinance to use the public data loader') from exc
    bars = yf.download(ticker.strip().upper(), start=begin.strftime('%Y-%m-%d'),
                       end=(finish + pd.Timedelta(days=1)).strftime('%Y-%m-%d'),
                       auto_adjust=False, progress=False, threads=False)
    if bars is None or bars.empty:
        return pd.DataFrame(columns=['Open','High','Low','Close','Volume'])
    if isinstance(bars.columns, pd.MultiIndex):
        bars.columns = bars.columns.get_level_values(0)
    expected = ['Open','High','Low','Close','Volume']
    missing = set(expected) - set(bars.columns)
    if missing:
        raise ValueError(f'Market data missing columns: {sorted(missing)}')
    result = bars.loc[:, expected].sort_index().copy()
    if cache is not None:
        cache.write(ticker.strip().upper(), result)
    return result
